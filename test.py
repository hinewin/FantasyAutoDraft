num_owners = int(input("Enter the total number of Fantasy owners in your league: "))
user_draft_position = int(input("Enter your draft position: "))
user_team_name = input("Enter your fantasy team name: ").strip() or "USER-TEAM"

# Generate Draft Order
draft_order = [f"Owner-Pick-Order-#{i}" for i in range(1, num_owners+1)]
draft_order[user_draft_position - 1] = f"{user_team_name}-draft-#-{user_draft_position}"

print (draft_order)
