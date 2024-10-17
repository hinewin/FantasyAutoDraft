import csv
import psycopg2
import os

# DB Conneciton
try:
    connection = psycopg2.connect(
        user = "postgres",
        password = os.getenv("POSTGRES_PWD",""),
        host = "localhost",
        port = "5433",
        database = "fantasy_draft"
    )

    cursor = connection.cursor()
    # Print PostgreSQL details
    print("PostgreSQL server information:")
    cursor.execute("SELECT version();")
    record = cursor.fetchone()
    print(record)

    # Drop the table if it already exists
    cursor.execute("""
        DROP TABLE IF EXISTS PlayerStats
    """)

 # create table 
    cursor.execute("""
        CREATE TABLE PlayerStats (
            Rank REAL PRIMARY KEY,
            Player TEXT,
            Pos TEXT,
            Team TEXT,
            GP INTEGER,
            MPG REAL,
            FG_Made REAL,
            FG_Attempted REAL,
            FT_Made REAL,
            FT_Attempted REAL,
            ThreePM REAL,
            PTS REAL,
            TREB REAL,
            AST REAL,
            STL REAL,
            BLK REAL,
            TOs REAL,
            TOTAL REAL
        );
    """)

    with open ('Hashtag-Projections - 10-15.csv', 'r') as file:
        # Create CSV reader
        csv_reader = csv.reader(file)
        data = [row for row in csv_reader]

        header = data[0]
        header[6:8] = ['FG_Made', 'FG_Attempted', 'FT_Made', 'FT_Attempted']
        data[0] = header

        for i in range(1, len(data)):
            # Check if the current line is a header line and skip it if it is
            if data[i][0] == 'R#':
                continue
            # splitting fg% and ft%
            fg_percentage, fg_values = data[i][6].split('(')
            fg_made, fg_attempted = fg_values.strip(')').split('/')

            ft_percentage, ft_values = data[i][7].split('(')
            ft_made, ft_attempted = ft_values.strip(')').split('/')

            # Print for debugging
            # print(f"FG_Made: {fg_made}, FG_Attempted: {fg_attempted}, FT_Made: {ft_made}, FT_Attempted: {ft_attempted}")
            data[i][6:8] = [fg_made, fg_attempted, ft_made, ft_attempted]


        for i in range(1, len(data)):
            if data[i][0] == 'R#':
                continue
            cursor.execute("""
                            INSERT INTO PlayerStats 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, data[i])

        # commit changes
        connection.commit()

except (Exception, psycopg2.Error) as error:
    print("Error while inserting data into table", error)
finally:
    # Close cursor and connection
    if cursor:
        cursor.close()
    if connection:
        connection.close()