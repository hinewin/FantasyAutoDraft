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
        self.draft_order = None

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
            for pick, team in enumerate(round_order):
                 # Store each pick as a list [pick number, team, empty space for player, empty space for rank]
                picks_order.append([pick + 1, team, "", ""])  # We add 1 to pick because Python's list indices start at 0
        print (f"Here is draft order: {picks_order}")
        self.draft_order = picks_order  # Add this line to store the draft order in your Draft instance
    
    def select_player(self, player_name):
        """ Select a player from the pool """

     #If name is a an exact match
        self.cursor.execute("""
        SELECT Rank, Player, Pos, Team
        FROM PlayerStats
        WHERE Player ILIKE %s
        AND Rank NOT IN (
            SELECT Rank
            FROM DraftedPlayers
        );
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
        WHERE Rank NOT IN (
            SELECT Rank
            FROM DraftedPlayers                    
        )
        ORDER BY similarity(Player, %s) DESC
        LIMIT 3;                                
        """, (player_name,))

        results = self.cursor.fetchall()
        return results

    def draft_player(self):
        """ Draft player, writing result to CSV & Database"""

        for row in self.draft_order:
            pick, team, _, _ = row
            while True:
                print(f"Now drafting: {team} at pick #: {pick}")
                player_choice = input("Provide Player Name or Rank to Draft: ")
                players = self.select_player(player_choice)

                if not players:
                    print("Could not find any players matching input.")
                    return False
                # If multiple players are found, ask user to select one
                elif isinstance(players[0], list):
                    print("Multiple players found, please select one:")
                    for i, player in enumerate(players, start=1):
                        print(f"{i}. {player['player']} (Rank: {player['rank']}, Team: {player['team']}, Position: {player['pos']})")
                    while True:
                        try:
                            selection = input("Enter the number of the player you want to draft: ")
                            if selection == "":
                                print("No player selected. Let's try again.")
                                continue
                            player = players[int(selection) - 1]  # -1 because list indexes start at 0
                            break
                        except KeyboardInterrupt:
                            print("\nDraft cancelled by user.")
                            return
                        except (ValueError, IndexError):
                            print("Invalid selection. Let's try again.")
                else:  # Exact player found
                    player = players

                # Confirm with the user before drafting
                confirm = input(f"Draft player {player['player']}, Rank {player['rank']}, from team {player['team']}, position {player['pos']}? (yes/no): ")
                if confirm.lower() in ["y", "yes"]:
                    # Insert player data into your 'DraftedPlayers' table in the database
                    self.cursor.execute("""
                        INSERT INTO DraftedPlayers (FantasyTeam, DraftPick, Player, Rank)
                        VALUES (%s, %s, %s, %s)
                    """, (team, pick, player['player'], player['rank']))  # team and pick come from the draft_order list
                    self.connection.commit()
                    # Save the drafted player's name and rank into the draft order list
                    row[2] = player['player']
                    row[3] = player['rank']
                    print(f"Player {player['player']} is successfully drafted by {team}!")
                    break
                else:
                    print("Draft cancelled for this player. Please choose another player.")
                

        # At the end of the drafting, save the draft order with all players into a CSV file
        with open('draft_order.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Pick Number', 'Team', 'Player Name', 'Rank'])  # Write header
            writer.writerows(self.draft_order)  # Write draft data

        print("Drafting complete. The final draft order has been saved to draft_order.csv")
                
    def calculate_team_stats(self, team):
        pass



    
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
            draft.create_draft_order()
            draft.draft_player()

        

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()