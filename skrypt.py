import pandas as pd
import os
import time
import re
import csv
import sys

# usuń z wiersza informacje, które są niepotrzebne i łatwo je zidentyfikować
def adjust_row(row):
    if len(row) > 27:
        if re.match('[0-9][0-9][a-z]',row[5]): 
            found = False
            delete = True
            unwanted = []
            i=6
            while not found:
                if i > len(row):
                    delete = False
                    break
                if row[i] == 'stations':
                    found = True
                else:
                    unwanted.append(i)
                    i+=1
        if delete:
            for ele in sorted(unwanted, reverse = True): 
                del row[ele]
    k=0
    for i in range(len(row)):
        if type(row[i])==int or (type(row[i])==str and re.match("^\d+$",row[i])):
            if int(row[i]) > 1700000000:
                el = i
                found = False
                j=el+1
                delete = True
                unwanted = []
                while not found:
                    if j >= len(row):
                        delete = False
                        break
                    if (type(row[j])==str and re.match('^[A-Z][A-Z]',row[j])):
                        found = True
                    else:
                        unwanted.append(j)
                        j+=1
                if delete:
                    for ele in sorted(unwanted, reverse = True): 
                        del row[ele]
                break
    if not ((type(row[14])==str and '.' in row[14]) or (type(row[14])==float)):
        x = -1
        for el1 in range(15,len(row)):
            if ((type(row[el1])==str and '.' in row[el1]) or (type(row[el1])==float)):
                x = el1
                break
        if x>0:
            unwanted = [i for i in range(13,x-1)]
            for ele in sorted(unwanted, reverse = True): 
                del row[ele]
    for i in range(len(row)):
        if type(row[i])==int or (type(row[i])==str and re.match("^\d+$",row[i])):
            el2 = -1
            if int(row[i]) > 1700000000:
                print(i)
                el2 = i
            if el2 != 17 and el2>0:
                unwanted = [i for i in range(16,el2-1)]
                print(el2)
                print(len(row))
                for ele in sorted(unwanted, reverse = True): 
                    del row[ele]
            break
    return row

# pobierz z wiersza tylko potrzebne dane
def ingest_data_from_row(row):
    r = []
    r.append(row[0])
    r.append(row[1])
    r.append(row[3])
    r.append(row[4])
    r.append(row[7])
    r.append(row[8])
    r.append(row[11])
    r.append(row[12])
    if row[-1] == '200':
        if re.match('[A-Z][A-Z]',row[-7]):
            r.append(row[-9])
            r.append(row[-8])
            r.append(row[-7])
        else:
            r.append(row[-8])
            r.append(row[-7])
            r.append(None)
        r.append(row[-6])
        r.append(row[-5])
        r.append(row[-4])
    else:
        if re.match('[A-Z][A-Z]',row[-8]):
            r.append(row[-10])
            r.append(row[-9])
            r.append(row[-8])
        else:
            r.append(row[-9])
            r.append(row[-8])
            r.append(None)
        r.append(row[-7])
        r.append(row[-6])
        r.append(row[-5])
    return r

columns = ['lon', 'lat', 'weather_main', 'weather_description',
       'temp', 'feels_like', 
       'pressure', 'humidity',
       'clouds_all', 'dt', 'country', 'sunrise',
       'sunset', 'timezone']

#stwórz prawidłowy plik .csv
def create_dataframe(path,file,time=False):
    rows = []
    file_path = path + file
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        
        for i,row1 in enumerate(csv_reader):
            if i!=0:
                # Liczymy liczbę elementów w danej linii
                if time:
                    row1.pop(-1)
                row2 = row1.copy()
                ingested = adjust_row(row2)
                rows.append(ingest_data_from_row(ingested))

    df = pd.DataFrame(rows,columns=columns)
    return df

def concat_data(path1, path2):
    files = [f for f in os.listdir(path1)]
    all_data = []
    for file in files:
        all_data.append(create_dataframe(path1,file,False))
    df_concat = pd.concat(all_data)
    filepath = path2+"all_data2.csv"
    df_concat.to_csv(filepath, index=False)


if __name__ == "__main__":
    concat_data('files/','cleaned_data/')



