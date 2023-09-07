import csv
import threading

DATABASE_PATH = './database.csv'

# Stores records of foxes and other animals
class Database():
    def __init__(self):
        self.lock = threading.Lock()

    # Save a record into the end of csv file
    def write_record(self, record: list):
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'a', newline='') as file: 
            writer = csv.writer(file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(record)

    # Get a list of all records
    def read_records(self):
        records = []
        # Acquire the lock to prevent a race condition and open the database
        with self.lock, open(DATABASE_PATH, 'r', newline='') as file:
            reader = csv.reader(file, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                records.append(row)
        return records
    
    # Delete the database
    def delete_database(self):
        with self.lock, open(DATABASE_PATH, 'w'):
            print('Database deleted')

if __name__ == "__main__":
    DATABASE_PATH = '../database.csv'
    db = Database()
    db.write_record(['first', 'second', 345])
    db.write_record([''])
    db.write_record(['''this is a loooooooooooong sentence!'''])

    print(db.read_records())
    db.delete_database()
    print(db.read_records())