import csv, random, string

with open("data/test_file.csv","w",newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id","name","age","city","salary"])
    cities = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Pune"]
    for i in range(100_000):
        writer.writerow([i, 
        ''.join(random.choices(string.ascii_lowercase, k=5)), 
        random.randint(18, 60), 
        random.choice(cities), 
        random.randint(30000, 100000),
        ])