example_data = {
    "games": [
        {"team_a": "Team 1", "team_b": "Team 2", "score_a": 21, "score_b": 14},
        {"team_a": "Team 3", "team_b": "Team 4", "score_a": 17, "score_b": 20},
    ],
    "standings": [
        {"team": "Team 1", "wins": 5, "losses": 2},
        {"team": "Team 2", "wins": 4, "losses": 3},
    ],
    # Minimal weekly sample to drive the teletext view
    "weekly_games": [
        {
            "team_a": "Team 1",
            "team_b": "Team 2",
            "score_a": 21,
            "score_b": 14,
            "status": "final",
            "start_time": "2025-08-10T17:00:00Z",
        },
        {
            "team_a": "Team 3",
            "team_b": "Team 4",
            "score_a": 10,
            "score_b": 7,
            "status": "final",
            "start_time": "2025-08-11T18:00:00Z",
        },
        {
            "team_a": "Team 5",
            "team_b": "Team 6",
            "score_a": 13,
            "score_b": 16,
            "status": "live",
            "start_time": "2025-08-18T16:00:00Z",
        },
        {
            "team_a": "Team 7",
            "team_b": "Team 8",
            "status": "upcoming",
            "start_time": "2025-08-19T19:30:00Z",
        },
        {
            "team_a": "Team 9",
            "team_b": "Team 10",
            "status": "upcoming",
            "start_time": "2025-08-20T20:15:00Z",
        },
    ],
}
