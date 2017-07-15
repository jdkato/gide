import sqlite3

import yaml

DATABASE = "packages.sqlite3"
CREATE_PACKAGE_TABLE = '''
CREATE TABLE Package (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name TEXT NOT NULL,
    stars INTEGER,
    url TEXT NOT NULL,
    license TEXT NOT NULL,
    description TEXT NOT NULL
);
'''

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

cursor.execute("DROP TABLE IF EXISTS 'Package'")
cursor.execute(CREATE_PACKAGE_TABLE)

with open('packages.yml') as data:
    packages = yaml.load(data)
    for sec in packages:
        for p in packages[sec]:
            cursor.execute(
                """
                INSERT INTO Package(name, stars, url, description, license)
                VALUES (?,?,?,?,?)
                """,
                [p['name'], p['stars'], p['url'], p['summary'], p['license']])

connection.commit()
connection.close()
