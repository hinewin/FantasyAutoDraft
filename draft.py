import argparse
import csv
import os
import psycopg2

from psycopg2.extras import DictCursor

class Draft:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = self.connection.cursor(cursor_factory=DictCursor)
        self.num_owners = None
        self.user_draft_position = None
        self.user_team_name = "***USER-TEAM***"
        self.total_rounds = 13
        self.current_pick = 1

        # Gather l

    def start_draft(self):
        """ Create a table to keep track of a draft """

        print ("Starting a new draft....")
        
        # Create DraftedPlayers table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS DraftedPlayers (
                FantasyTeam TEXT,
                DraftPick INTEGER,
                Player TEXT,
                Rank REAL PRIMARY KEY
                );
        """)

        # Create FantasyTeamStats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS FantasyTeamStats (
                FantasyTeam TEXT PRIMARY KEY,
                TotalPlayers INTEGER,
                TotalPoints REAL,
                PickOrderNum INTEGER
            );
        """)

        self.connection.commit()

    def reset_draft(self):
        """Reset the draft state - call this when we want to start over"""
        self.cursor.execute("""
            DROP TABLE IF EXISTS DraftedPlayers; DROP TABLE IF EXISTS FantasyTeamStats;
        """)
        self.connection.commit()
        print ("Draft state has been reset.")

    def create_draft_order(self):
        """ Generate Draft Order"""

        # Gather league and draft details
        self.num_owners = int(input("Enter the total number of Fantasy owners in your league: "))
        self.user_draft_position = int(input("Enter your draft position: "))
        team_name_input = input("Enter your fantasy team name: ")
        if team_name_input:
            self.user_team_name = team_name_input
        total_rounds_input = input("(Optional) Total # of rounds in your draft - Default to standard 13: ")
        if total_rounds_input:  # replace the default number of rounds if user gives input
            self.total_rounds = int(total_rounds_input)


        # Generate Draft Order
        initial_order = [f"Owner-#{i}" for i in range(1, self.num_owners+1)]
        initial_order[self.user_draft_position - 1] = f"{self.user_team_name}"

        picks_order = []

        for draft_round in range(self.total_rounds):
            round_order = initial_order if draft_round % 2 == 0 else initial_order[::-1] # Initial order if round is even
            picks_order.extend(round_order)

        with open('draft_order.csv', 'w', newline='', encoding='utf-8') as draft_csvfile:
            writer = csv.writer(draft_csvfile)
            headers = ['Team', 'Pick Number', 'Player Name', 'Rank', 'Position', 'Team', 'Projected Fantasy PT']
            writer.writerow(headers)
            for pick, team in enumerate(picks_order, start=1):
                writer.writerow([pick, team] + [""] * (len(headers) - 2)) # Leave empty value for other headers

        return picks_order
    
    def select_player(self, player_name):
        """ Select a player from the pool """

     #If name is a an exact match
        self.cursor.execute("""
        SELECT Rank, Player, Pos, Team FROM PlayerStats WHERE Player ILIKE %s;
        """,(player_name,))
        result = self.cursor.fetchone()
        print (result)

        # If an exact match is found, return it
        if result is not None:
            return result
        
        # If no exact match is found, then perform a similarity search
        self.cursor.execute("""
        SELECT Rank, Player, Pos, Team
        FROM PLayerStats
        ORDER BY similarity(Player, %s) DESC
        LIMIT 3;                                
        """, (player_name,))

        results = self.cursor.fetchall()
        return results

    def draft_player(self):
        while True:
            player_choice = input("Provide Player Name or Rank to Draft: ")

            # Use `select_player` function
            players = self.select_player(player_choice)

            if not players:
                print("Could not find any players matching input.")
                return False

            # If multiple players are found, ask user to select one
            elif isinstance(players[0], list) :
                print("Multiple players found, please select one:")
                for i, player in enumerate(players, start=1):
                    print(f"{i}. {player['player']} (Rank: {player['rank']}, Team: {player['team']}, Position: {player['pos']})")
                while True:
                    try:
                        selection = input("Enter the number of the player you want to draft: ")
                        if selection == "":
                            print("No player selected. Let's try again.")
                            continue
                        player = players[int(selection) - 1] # -1 because list indexes start at 0
                        break
                    except KeyboardInterrupt:
                        print("\nDraft cancelled by user.")
                        return
                    except (ValueError, IndexError):
                        print("Invalid selection. Let's try again.")

            else: # Exact player found
                player = players

            # Confirm with the user before drafting
            confirm = input(f"Draft player {player['player']}, Rank {player['rank']}, from team {player['team']}, position {player['pos']}? (yes/no): ")

            if confirm.lower() in ["y", "yes"]:
            # Insert player data into your 'DraftedPlayers' table in the database
                self.cursor.execute("""
                    INSERT INTO DraftedPlayers (FantasyTeam, DraftPick, Player, Rank)
                    VALUES (%s, %s, %s, %s)
                """, (self.user_team_name, self.current_pick, player['player'], player['rank']))

                self.connection.commit()
            # Write player data into the CSV
            with open('draft_order.csv', 'a', newline='') as csvfile:
                fieldnames = ['FantasyTeam', 'DraftPick', 'Player', 'Rank']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writerow({
                    'FantasyTeam': self.user_team_name, 
                    'DraftPick': self.current_pick, 
                    'Player': player['player'], 
                    'Rank': player['rank']
                })
                print(f"Player data successfully added to draft.csv")

            print(f"Successfully drafted {player['player']} by {self.user_team_name}!")
            self.current_pick += 1 # Move to next pick

                

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-R", "--reset-draft", help="Reset draft", action="store_true")
    parser.add_argument("-S", "--start-draft", help="Start draft", action="store_true")
    args = parser.parse_args()

    try:
        connection = psycopg2.connect(
            user = "postgres",
            password = os.getenv("POSTGRES_PWD",""),
            host = "localhost",
            port = "5433",
            database = "fantasy_draft"
        )
        
        draft = Draft(connection)

        if args.reset_draft:
            draft.reset_draft()
        
        if args.start_draft:
            draft.start_draft()
            draft.draft_player()

        

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()