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
        print ("[DB] Created DraftedPlayers Table")
        # Create FantasyTeamStats table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS FantasyTeamStats (
                FantasyTeam TEXT PRIMARY KEY,
                TotalGP REAL,
                TotalMPG REAL,
                TotalFG_Made REAL,
                TotalFG_Attempt REAL,
                TotalFT_Attempt REAL,
                TotalFT_Made REAL,
                TotalThree_Made REAL,
                TotalPoints REAL, 
                TotalRebounds REAL,
                TotalAssists REAL,
                TotalSteals REAL,
                TotalBlocks REAL,
                TotalTurnovers REAL,
                TotalFantasyPt REAL
            );
         """)

        self.connection.commit()
        print ("[DB] Created FantasyTeamStats Table")


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
        overall_pick = 1
        for row in self.draft_order:
            pick, team, _, _ = row
            while True:
                print(f"Now drafting: {team} at pick #: {overall_pick}")
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
                    row[0] = overall_pick
                    # Insert player data into your 'DraftedPlayers' table in the database
                    self.cursor.execute("""
                        INSERT INTO DraftedPlayers (FantasyTeam, DraftPick, Player, Rank)
                        VALUES (%s, %s, %s, %s)
                    """, (team, overall_pick, player['player'], player['rank']))  # team and pick come from the draft_order list
                    self.connection.commit()
                    print ("[DB] Inserted values into DraftedPlayers Table")
                    # Save the drafted player's name and rank into the draft order list
                    row[2] = player['player']
                    row[3] = player['rank']
                    print(f"Player {player['player']} is successfully drafted by {team}!")
                    overall_pick += 1
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
        """Calculates and updates statistics for a particular fantasy team."""
       
        # Fetch all players from drafted players for the team
        self.cursor.execute("""
            SELECT Rank FROM DraftedPlayers WHERE FantasyTeam = %s
        """, (team,))

        drafted_ranks = self.cursor.fetchall()

        # Initialize stats
        total_stats = {
        "TotalGP": 0,
        "TotalMPG": 0,
        "TotalFG_Made": 0,
        "TotalFG_Attempt": 0,
        "TotalFT_Attempt": 0,
        "TotalFT_Made": 0,
        "TotalThree_Made": 0,
        "TotalPoints": 0, 
        "TotalRebounds": 0,
        "TotalAssists": 0,
        "TotalSteals": 0,
        "TotalBlocks": 0,
        "TotalTurnovers": 0,
        "TotalFantasyPt": 0
        }

        # Iterate over each player and get their stats
        for (rank,) in drafted_ranks:
            self.cursor.execute("""
                SELECT GP, MPG, FG_Made, FG_Attempted, FT_Attempted, FT_Made, ThreePM, 
                Pts, TREB, AST, STL, BLK, TOs, TOTAL 
                FROM PlayerStats WHERE Rank = %s
            """, (rank,))

            player_stats = self.cursor.fetchone()
            # Update stats
            total_stats["TotalGP"] += player_stats["gp"]
            total_stats["TotalMPG"] += player_stats["mpg"]
            total_stats["TotalFG_Made"] += player_stats["fg_made"]
            total_stats["TotalFG_Attempt"] += player_stats["fg_attempted"]
            total_stats["TotalFT_Attempt"] += player_stats["ft_attempted"]
            total_stats["TotalFT_Made"] += player_stats["ft_made"]
            total_stats["TotalThree_Made"] += player_stats["threepm"]
            total_stats["TotalPoints"] += player_stats["pts"]
            total_stats["TotalRebounds"] += player_stats["treb"]
            total_stats["TotalAssists"] += player_stats["ast"]
            total_stats["TotalSteals"] += player_stats["stl"]
            total_stats["TotalBlocks"] += player_stats["blk"]
            total_stats["TotalTurnovers"] += player_stats["tos"]
            total_stats["TotalFantasyPt"] += player_stats["total"]

        # Insert to `FantasyTeamStats` Table
        self.cursor.execute("""
                INSERT INTO FantasyTeamStats (
                    FantasyTeam, 
                    TotalGP, 
                    TotalMPG, 
                    TotalFG_Made, 
                    TotalFG_Attempt, 
                    TotalFT_Attempt, 
                    TotalFT_Made, 
                    TotalThree_Made, 
                    TotalPoints, 
                    TotalRebounds, 
                    TotalAssists, 
                    TotalSteals, 
                    TotalBlocks, 
                    TotalTurnovers, 
                    TotalFantasyPt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (FantasyTeam) DO UPDATE SET 
                TotalGP=excluded.TotalGP, 
                TotalMPG=excluded.TotalMPG, 
                TotalFG_Made=excluded.TotalFG_Made,
                TotalFG_Attempt=excluded.TotalFG_Attempt,
                TotalFT_Attempt=excluded.TotalFT_Attempt,
                TotalFT_Made=excluded.TotalFT_Made,
                TotalThree_Made=excluded.TotalThree_Made,
                TotalPoints=excluded.TotalPoints,
                TotalRebounds=excluded.TotalRebounds,
                TotalAssists=excluded.TotalAssists,
                TotalSteals=excluded.TotalSteals,
                TotalBlocks=excluded.TotalBlocks,
                TotalTurnovers=excluded.TotalTurnovers,
                TotalFantasyPt=excluded.TotalFantasyPt
    """, (team,
          total_stats["TotalGP"], 
          total_stats["TotalMPG"], 
          total_stats["TotalFG_Made"], 
          total_stats["TotalFG_Attempt"], 
          total_stats["TotalFT_Attempt"], 
          total_stats["TotalFT_Made"], 
          total_stats["TotalThree_Made"], 
          total_stats["TotalPoints"], 
          total_stats["TotalRebounds"], 
          total_stats["TotalAssists"], 
          total_stats["TotalSteals"], 
          total_stats["TotalBlocks"], 
          total_stats["TotalTurnovers"], 
          total_stats["TotalFantasyPt"]))
        self.connection.commit()

    def show_team_stats(self):
        """Retrieves and shows the total statistics for each fantasy team."""

        # Retrieve the stats for all teams
        self.cursor.execute("""
            SELECT * FROM FantasyTeamStats
        """)

        stats = self.cursor.fetchall()

        # Now print the stats for each team
        for stat in stats:
            print(f"Stats for {stat['fantasyteam']}:")
            print(f"Total GP: {stat['totalgp']}")
            print(f"Total MPG: {stat['totalmpg']}")

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

            for _, team, _, _ in draft.draft_order:
                draft.calculate_team_stats(team)
            draft.show_team_stats()

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()