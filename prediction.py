class PredictiveModel:
    def __init__(self, draft):
        self.draft = draft

    def analyze_user_team(self, user_team):
        '''Analyze the user's team stats by averaging the ranks of the players.'''
        user_team = self.draft.get_user_team(user_team)
        total_rank = 0
        if user_team:
            for player in user_team:
                total_rank += player['rank']
            average_rank = total_rank / len(user_team) if user_team else None
            return average_rank
        else:
            print ("No players in user's team")

    def predict_opponent_picks(self):
        """Predict the opponents' picks based on the highest rank available."""
        total_picks_so_far = self.draft.overall_pick - 1
        current_round = total_picks_so_far // self.draft.picks_per_round

        if current_round % 2 == 0:  # odd round in draft
            if self.draft.user_draft_position > self.draft.overall_pick:
                num_picks_until_your_turn = self.draft.user_draft_position - self.draft.overall_pick
            else:
                num_picks_until_your_turn = self.draft.num_owners * 2 - (self.draft.overall_pick - self.draft.user_draft_position)
        else:  # even round in draft
            if (self.draft.num_owners * 2) - self.draft.user_draft_position >= self.draft.overall_pick:
                num_picks_until_your_turn = (self.draft.num_owners * 2) - self.draft.user_draft_position - self.draft.overall_pick
            else:
                num_picks_until_your_turn = self.draft.user_draft_position

        print(f"num_picks_until_your_turn: {num_picks_until_your_turn}")  # Debugging print
        likely_drafted = self.draft.get_available_players(num_picks_until_your_turn)

        return likely_drafted

    def rank_players(self):
        '''Rank available players based on their ranks, excluding those who are likely to be picked by opponents.'''
        
        # Get the players likely to be picked by opponents before your next turn
        likely_picked = self.predict_opponent_picks()

        # Get all available players
        available_players = self.draft.get_available_players(len(likely_picked)+3)


        # Exclude the likely picked players from the available_players
        ranked_players = [player for player in available_players if player not in likely_picked]

        return ranked_players
    