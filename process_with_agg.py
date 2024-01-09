from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, FloatType
from datetime import datetime, timedelta
from pyspark.sql import Window
from pyspark.sql.functions import col, date_format, when, row_number, unix_timestamp, regexp_replace, monotonically_increasing_id
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("WeatherDataProcessing").getOrCreate()

def convert_timezone(value):
    return value / 3600

def convert_datetime(timestamp, timezone_offset):
    dt = datetime.utcfromtimestamp(timestamp)

    dt_with_offset = dt + timedelta(hours=timezone_offset)

    return dt_with_offset.strftime("%Y-%m-%d %H:%M:%S")

def convert_temperature(value):
    return value - 273.15

convert_timezone_udf = udf(convert_timezone, FloatType())
convert_datetime_udf = udf(convert_datetime, StringType())
convert_temperature_udf = udf(convert_temperature, FloatType())

df = spark.read.option("header","true").option("inferschema","true").option("sep", ",").csv("hdfs://localhost:8020/all_data.csv")

df = df.withColumn("timezone", convert_timezone_udf(df["timezone"]))
df = df.withColumn("dt", convert_datetime_udf(df["dt"], df["timezone"]))
df = df.withColumn("sunrise", convert_datetime_udf(df["sunrise"], df["timezone"]))
df = df.withColumn("sunset", convert_datetime_udf(df["sunset"], df["timezone"]))
df = df.withColumn("temp", convert_temperature_udf(df["temp"]))
df = df.withColumn("feels_like", convert_temperature_udf(df["feels_like"]))

df = df.withColumn("sunrise", col("sunrise").cast("timestamp"))
df = df.withColumn("sunset", col("sunset").cast("timestamp"))

df = df.withColumn("day_time", (unix_timestamp("sunset") - unix_timestamp("sunrise")) / 3600)

df = df.withColumn("date", date_format(col("dt"), "yyyy-MM-dd"))

df = df.withColumn("time", date_format(col("dt"), "HH:mm:ss"))
df = df.drop("dt")

df = df.withColumn("part_of_day", 
                   when((col("time") >= "00:00:00") & (col("time") < "06:00:00"), "night")
                   .when((col("time") >= "06:00:00") & (col("time") < "12:00:00"), "morning")
                   .when((col("time") >= "12:00:00") & (col("time") < "18:00:00"), "afternoon")
                   .otherwise("evening"))


cities = spark.read.option("header","true").option("inferschema","true",).option("sep", ";").csv("hdfs://localhost:8020/worldcities_selected.csv")

cities = cities.withColumn("lat", regexp_replace(col("lat"), ",", "."))
cities = cities.withColumn("lng", regexp_replace(col("lng"), ",", "."))

cities = cities.withColumn("lat", col("lat").cast("double"))
cities = cities.withColumn("lng", col("lng").cast("double"))

df_merged = df.join(cities, (df["lat"] == cities["lat"]) & (df["lon"] == cities["lng"]), "inner")
df_not_merged = df.join(cities, (df["lat"] == cities["lat"]) & (df["lon"] == cities["lng"]), "left_outer")
df_not_merged = df_not_merged.filter(col("city").isNull())

df_merged = df_merged.drop(cities['country'])
df_merged = df_merged.drop(cities['lat'])

df_not_merged = df_not_merged.drop(cities['country'])
df_not_merged = df_not_merged.drop(cities['lat'])

grouped_df = df_merged.groupBy(["lon", "lat", "country", "sunrise", "sunset", "timezone", 
                         "day_time", "date", "time", "part_of_day", "city", "city_ascii", 
                         "lng", "iso2", "iso3", "admin_name", "capital", "population", "id"])

aggregated_df = grouped_df.agg(
    F.mean("temp").alias("mean_temp"),
    F.mean("feels_like").alias("mean_feels_like"),
    F.mean("pressure").alias("mean_pressure"),
    F.mean("humidity").alias("mean_humidity"),
    F.mean("clouds_all").alias("mean_clouds_all")
)

weather_main_mode = (df_merged.groupBy(["lon", "lat", "country", "sunrise", "sunset", "timezone", 
                                 "day_time", "date", "time", "part_of_day", "city", "city_ascii", 
                                 "lng", "iso2", "iso3", "admin_name", "capital", 
                                 "population", "id", "weather_main"])
                     .count()
                     .withColumn("rn", row_number().over(Window.partitionBy(["lon", "lat", "country", 
                                                                            "sunrise", "sunset", "timezone", 
                                                                            "day_time", "date", "time", "part_of_day", 
                                                                            "city", "city_ascii", "lng", "iso2", "iso3", 
                                                                            "admin_name", "capital", "population", "id"])
                                                     .orderBy(col("count").desc())))
                     .filter(col("rn") == 1)
                     .drop("rn", "count"))

weather_description_mode = (df_merged.groupBy(["lon", "lat", "country", "sunrise", "sunset", "timezone", 
                                        "day_time", "date", "time", "part_of_day", "city", "city_ascii", 
                                        "lng", "iso2", "iso3", "admin_name", "capital", 
                                        "population", "id", "weather_description"])
                            .count()
                            .withColumn("rn", row_number().over(Window.partitionBy(["lon", "lat", "country", 
                                                                                   "sunrise", "sunset", "timezone", 
                                                                                   "day_time", "date", "time", "part_of_day", 
                                                                                   "city", "city_ascii", "lng", "iso2", "iso3", 
                                                                                   "admin_name", "capital", "population", "id"])
                                                            .orderBy(col("count").desc())))
                            .filter(col("rn") == 1)
                            .drop("rn", "count"))

aggregated_df = aggregated_df.join(weather_main_mode, ["lon", "lat", "country", "sunrise", "sunset", 
                                                       "timezone", "day_time", "date", "time", 
                                                       "part_of_day", "city", "city_ascii", "lng", 
                                                       "iso2", "iso3", "admin_name", "capital", 
                                                       "population", "id"], "left_outer")

aggregated_df = aggregated_df.join(weather_description_mode, ["lon", "lat", "country", "sunrise", "sunset", 
                                                              "timezone", "day_time", "date", "time", 
                                                              "part_of_day", "city", "city_ascii", "lng", 
                                                              "iso2", "iso3", "admin_name", "capital", 
                                                              "population", "id"], "left_outer")

df_final = aggregated_df
df_final = df_final.withColumn("id", monotonically_increasing_id())
df_final.write.csv("hdfs://localhost:8020/output_csv18", header=True)
df_not_merged.write.csv("hdfs://localhost:8020/output_not_merged_csv18", header=True)

spark.stop()
