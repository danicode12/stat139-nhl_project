import requests
import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta
import time

# NHL ARENA COORDINATES MANUALLY GRABBED FROM WIKIPEDIA
ARENA_COORDS = {
    'ANA': {'name': 'Anaheim Ducks', 'arena': 'Honda Center', 'lat': 33.8078, 'lon': -117.8765},
    'ARI': {'name': 'Arizona Coyotes', 'arena': 'Mullett Arena', 'lat': 33.4255, 'lon': -111.9325},
    'BOS': {'name': 'Boston Bruins', 'arena': 'TD Garden', 'lat': 42.3662, 'lon': -71.0621},
    'BUF': {'name': 'Buffalo Sabres', 'arena': 'KeyBank Center', 'lat': 42.8750, 'lon': -78.8764},
    'CGY': {'name': 'Calgary Flames', 'arena': 'Scotiabank Saddledome', 'lat': 51.0374, 'lon': -114.0519},
    'CAR': {'name': 'Carolina Hurricanes', 'arena': 'PNC Arena', 'lat': 35.8033, 'lon': -78.7220},
    'CHI': {'name': 'Chicago Blackhawks', 'arena': 'United Center', 'lat': 41.8807, 'lon': -87.6742},
    'COL': {'name': 'Colorado Avalanche', 'arena': 'Ball Arena', 'lat': 39.7487, 'lon': -105.0077},
    'CBJ': {'name': 'Columbus Blue Jackets', 'arena': 'Nationwide Arena', 'lat': 39.9692, 'lon': -83.0060},
    'DAL': {'name': 'Dallas Stars', 'arena': 'American Airlines Center', 'lat': 32.7905, 'lon': -96.8103},
    'DET': {'name': 'Detroit Red Wings', 'arena': 'Little Caesars Arena', 'lat': 42.3411, 'lon': -83.0553},
    'EDM': {'name': 'Edmonton Oilers', 'arena': 'Rogers Place', 'lat': 53.5469, 'lon': -113.4979},
    'FLA': {'name': 'Florida Panthers', 'arena': 'FLA Live Arena', 'lat': 26.1584, 'lon': -80.3256},
    'LAK': {'name': 'Los Angeles Kings', 'arena': 'Crypto.com Arena', 'lat': 34.0430, 'lon': -118.2673},
    'MIN': {'name': 'Minnesota Wild', 'arena': 'Xcel Energy Center', 'lat': 44.9448, 'lon': -93.1019},
    'MTL': {'name': 'Montreal Canadiens', 'arena': 'Bell Centre', 'lat': 45.4961, 'lon': -73.5693},
    'NSH': {'name': 'Nashville Predators', 'arena': 'Bridgestone Arena', 'lat': 36.1592, 'lon': -86.7785},
    'NJD': {'name': 'New Jersey Devils', 'arena': 'Prudential Center', 'lat': 40.7334, 'lon': -74.1712},
    'NYI': {'name': 'New York Islanders', 'arena': 'UBS Arena', 'lat': 40.7172, 'lon': -73.7246},
    'NYR': {'name': 'New York Rangers', 'arena': 'Madison Square Garden', 'lat': 40.7505, 'lon': -73.9934},
    'OTT': {'name': 'Ottawa Senators', 'arena': 'Canadian Tire Centre', 'lat': 45.2969, 'lon': -75.9269},
    'PHI': {'name': 'Philadelphia Flyers', 'arena': 'Wells Fargo Center', 'lat': 39.9012, 'lon': -75.1720},
    'PIT': {'name': 'Pittsburgh Penguins', 'arena': 'PPG Paints Arena', 'lat': 40.4395, 'lon': -79.9892},
    'SJS': {'name': 'San Jose Sharks', 'arena': 'SAP Center', 'lat': 37.3327, 'lon': -121.9012},
    'SEA': {'name': 'Seattle Kraken', 'arena': 'Climate Pledge Arena', 'lat': 47.6221, 'lon': -122.3540},
    'STL': {'name': 'St. Louis Blues', 'arena': 'Enterprise Center', 'lat': 38.6268, 'lon': -90.2025},
    'TBL': {'name': 'Tampa Bay Lightning', 'arena': 'Amalie Arena', 'lat': 27.9427, 'lon': -82.4521},
    'TOR': {'name': 'Toronto Maple Leafs', 'arena': 'Scotiabank Arena', 'lat': 43.6435, 'lon': -79.3791},
    'VAN': {'name': 'Vancouver Canucks', 'arena': 'Rogers Arena', 'lat': 49.2778, 'lon': -123.1089},
    'VGK': {'name': 'Vegas Golden Knights', 'arena': 'T-Mobile Arena', 'lat': 36.1030, 'lon': -115.1784},
    'WSH': {'name': 'Washington Capitals', 'arena': 'Capital One Arena', 'lat': 38.8981, 'lon': -77.0212},
    'WPG': {'name': 'Winnipeg Jets', 'arena': 'Canada Life Centre', 'lat': 49.8928, 'lon': -97.1437},
}

# helpers for distance, location and travel distance (things we need to calcualte later! not important to analyze)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.
    """
    R = 3959  # Earth's radius in miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def get_team_location(team_abbrev):
    """Get lat/lon for a team."""
    if team_abbrev in ARENA_COORDS:
        return ARENA_COORDS[team_abbrev]['lat'], ARENA_COORDS[team_abbrev]['lon']
    return None, None


def calculate_travel_distance(prev_location, curr_location, is_home):
    """
    Calculate travel distance from previous game location to current game.
    If playing at home, travel is from prev_location to home arena.
    If playing away, travel is from prev_location to away arena.
    """
    if prev_location is None or curr_location is None:
        return np.nan
    
    prev_lat, prev_lon = prev_location
    curr_lat, curr_lon = curr_location
    
    if prev_lat is None or curr_lat is None:
        return np.nan
    
    return haversine_distance(prev_lat, prev_lon, curr_lat, curr_lon)

# NHL api funcs, no API key needed, public!

def get_season_schedule(season):
    """
    Fetch all regular season games for a given season.
    Season format: "20232024" for 2023-24 season
    """
    # The NHL API provides schedule by date range
    # Regular season typically runs October to April
    
    start_year = int(season[:4])
    end_year = int(season[4:])
    
    all_games = []
    
    # Iterate through each day of the season (October to April)
    start_date = datetime(start_year, 10, 1)
    end_date = datetime(end_year, 4, 30)
    
    current_date = start_date
    
    print(f"Fetching {season[:4]}-{season[4:6]} season schedule...")
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        try:
            url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract games from the response
                for game_week in data.get('gameWeek', []):
                    for game in game_week.get('games', []):
                        # Only include regular season games (gameType == 2)
                        if game.get('gameType') == 2:
                            all_games.append(game)
            
            # Be nice to the API
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error fetching {date_str}: {e}")
        
        # Move to next week (API returns weekly data)
        current_date += timedelta(days=7)
    
    print(f"Found {len(all_games)} regular season games")
    return all_games


def get_season_schedule_v2(season):
    """
    Fetch schedule using club-schedule-season endpoint for each team.
    API: https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}
    
    Example: https://api-web.nhle.com/v1/club-schedule-season/TOR/20232024
    """
    start_year = int(season[:4])
    end_year = int(season[4:])
    
    all_games = {}  # Use dict to avoid duplicates (key = game_id)
    
    print(f"Fetching {start_year}-{str(end_year)[2:]} season schedule...")
    print(f"Using NHL API: https://api-web.nhle.com/v1/club-schedule-season/TEAM/{season}")
    
    for team_abbrev in ARENA_COORDS.keys():
        try:
            # Get the full season schedule for this team
            url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_abbrev}/{season}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                for game in data.get('games', []):
                    # Only regular season (gameType == 2)
                    if game.get('gameType') == 2:
                        game_id = game.get('id')
                        if game_id not in all_games:
                            all_games[game_id] = game
                
                print(f"  ✓ {team_abbrev}: {len([g for g in data.get('games', []) if g.get('gameType') == 2])} games")
            else:
                print(f"  ✗ {team_abbrev}: HTTP {response.status_code}")
            
            time.sleep(0.25)  # Rate limiting - be nice to the API
            
        except requests.exceptions.Timeout:
            print(f"  ✗ {team_abbrev}: Timeout")
        except Exception as e:
            print(f"  ✗ {team_abbrev}: {e}")
    
    games_list = list(all_games.values())
    print(f"\n{'='*40}")
    print(f"Found {len(games_list)} unique regular season games")
    print(f"Expected: ~1312 games per season (82 games × 32 teams ÷ 2)")
    return games_list


def parse_game_data(games):
    """
    Parse raw game data into a structured format.
    Each game creates TWO rows (one for each team's perspective).
    """
    records = []
    
    for game in games:
        try:
            game_id = game.get('id')
            game_date = game.get('gameDate', '')[:10]  # YYYY-MM-DD
            
            # Get team info
            away_team = game.get('awayTeam', {})
            home_team = game.get('homeTeam', {})
            
            away_abbrev = away_team.get('abbrev')
            home_abbrev = home_team.get('abbrev')
            
            away_score = away_team.get('score', np.nan)
            home_score = home_team.get('score', np.nan)
            
            # Skip games that haven't been played yet
            if away_score is None or home_score is None:
                continue
                
            # Record from HOME team's perspective
            records.append({
                'game_id': game_id,
                'date': game_date,
                'team': home_abbrev,
                'opponent': away_abbrev,
                'home_away': 'home',
                'goals_for': home_score,
                'goals_against': away_score,
                'goal_diff': home_score - away_score,
                'game_location': home_abbrev,  # Game played at home team's arena
            })
            
            # Record from AWAY team's perspective
            records.append({
                'game_id': game_id,
                'date': game_date,
                'team': away_abbrev,
                'opponent': home_abbrev,
                'home_away': 'away',
                'goals_for': away_score,
                'goals_against': home_score,
                'goal_diff': away_score - home_score,
                'game_location': home_abbrev,  # Game played at home team's arena
            })
            
        except Exception as e:
            print(f"Error parsing game {game.get('id', 'unknown')}: {e}")
            continue
    
    return pd.DataFrame(records)


# DERIVED VARIABLE CALCULATIONS - THERE IS NO OPEN DATASET FOR THESE(INCLUDES REST DAYS, TRAVEL DISTANCE)

def calculate_rest_days(df):
    """Calculate days of rest since team's previous game."""
    df = df.sort_values(['team', 'date']).copy()
    df['date'] = pd.to_datetime(df['date'])
    
    df['prev_game_date'] = df.groupby('team')['date'].shift(1)
    df['rest_days'] = (df['date'] - df['prev_game_date']).dt.days
    
    # First game of season will have NaN
    return df


def calculate_travel_distances(df):
    """Calculate travel distance from previous game location."""
    df = df.sort_values(['team', 'date']).copy()
    
    # Get previous game location for each team
    df['prev_game_location'] = df.groupby('team')['game_location'].shift(1)
    
    travel_distances = []
    
    for idx, row in df.iterrows():
        if pd.isna(row['prev_game_location']):
            travel_distances.append(np.nan)
        else:
            # Get coordinates
            prev_lat, prev_lon = get_team_location(row['prev_game_location'])
            curr_lat, curr_lon = get_team_location(row['game_location'])
            
            if prev_lat and curr_lat:
                dist = haversine_distance(prev_lat, prev_lon, curr_lat, curr_lon)
                travel_distances.append(dist)
            else:
                travel_distances.append(np.nan)
    
    df['travel_distance'] = travel_distances
    return df


def calculate_opponent_win_pct(df):
    """
    Calculate opponent's win percentage at the time of the game.
    This requires calculating running win totals for each team.
    """
    df = df.sort_values(['date', 'game_id']).copy()
    
    # Initialize tracking dictionaries
    team_wins = {team: 0 for team in ARENA_COORDS.keys()}
    team_games = {team: 0 for team in ARENA_COORDS.keys()}
    
    opponent_win_pcts = []
    
    # Process games in chronological order
    # We need to process by unique games (not team-perspectives)
    processed_games = set()
    
    for idx, row in df.iterrows():
        team = row['team']
        opponent = row['opponent']
        
        # Calculate opponent's win pct BEFORE this game
        if team_games[opponent] > 0:
            opp_win_pct = team_wins[opponent] / team_games[opponent]
        else:
            opp_win_pct = np.nan  # No games played yet
        
        opponent_win_pcts.append(opp_win_pct)
        
        # Update records AFTER recording (only once per game)
        game_id = row['game_id']
        if game_id not in processed_games:
            processed_games.add(game_id)
            
            # Determine winner
            if row['goal_diff'] > 0:
                # Current team won
                team_wins[team] += 1
            elif row['goal_diff'] < 0:
                # Opponent won
                team_wins[opponent] += 1
            # Ties go to OT/SO - NHL counts as win for someone
            # The goal_diff should reflect the final score
            
            team_games[team] += 1
            team_games[opponent] += 1
    
    df['opponent_win_pct'] = opponent_win_pcts
    return df

def main():
    """Main function to extract and process NHL data."""
    
    seasons = ['20222023', '20232024']
    all_data = []
    
    for season in seasons:
        print(f"\n{'='*50}")
        print(f"Processing {season[:4]}-{season[4:]} season")
        print('='*50)
        
        # Fetch games
        games = get_season_schedule_v2(season)
        
        if not games:
            print(f"No games found for {season}")
            continue
        
        # Parse into DataFrame
        df = parse_game_data(games)
        df['season'] = f"{season[:4]}-{season[4:6]}"
        
        print(f"Parsed {len(df)} team-game records")
        
        all_data.append(df)
    
    # Combine all seasons
    if not all_data:
        print("No data collected!")
        return
    
    df = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal records: {len(df)}")
    
    # Calculate derived variables
    print("\nCalculating rest days...")
    df = calculate_rest_days(df)
    
    print("Calculating travel distances...")
    df = calculate_travel_distances(df)
    
    print("Calculating opponent win percentages...")
    df = calculate_opponent_win_pct(df)
    
    # Create binary home indicator
    df['is_home'] = (df['home_away'] == 'home').astype(int)
    
    # Select and order final columns
    final_columns = [
        'season',
        'date',
        'game_id',
        'team',
        'opponent',
        'is_home',
        'goals_for',
        'goals_against',
        'goal_diff',
        'rest_days',
        'travel_distance',
        'opponent_win_pct'
    ]
    
    df_final = df[final_columns].copy()
    
    # Sort by date and team
    df_final = df_final.sort_values(['season', 'date', 'team'])
    
    # Save to CSV
    output_file = 'nhl_travel_fatigue_data.csv'
    df_final.to_csv(output_file, index=False)
    
    print(f"\n{'='*50}")
    print(f"SUCCESS! Data saved to: {output_file}")
    print(f"{'='*50}")
    print(f"\nDataset Summary:")
    print(f"  Total records: {len(df_final)}")
    print(f"  Seasons: {df_final['season'].unique()}")
    print(f"  Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    print(f"\nColumn Statistics:")
    print(df_final.describe())
    
    # Show sample
    print(f"\nSample rows:")
    print(df_final.head(10))
    
    return df_final


if __name__ == "__main__":
    df = main()