import os
import boto3
from datetime import datetime

# Use environment variable to determine if using DynamoDB or local storage
USE_DYNAMODB = os.environ.get('USE_DYNAMODB', 'False').lower() == 'true'

# Initialize database connections based on environment
if USE_DYNAMODB:
    # DynamoDB setup for production
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("GameHistory")
    print("Using DynamoDB backend")
else:
    # Local in-memory database for development
    game_records = []
    print("Using local in-memory backend")

def save_game(user_id, user_move, ai_move, ai_type, result):
    """
    Saves a game record to the database.
    """
    timestamp = str(datetime.utcnow())
    
    if USE_DYNAMODB:
        # DynamoDB implementation
        table.put_item(
            Item={
                "user_id": user_id,
                "timestamp": timestamp,
                "user_move": user_move,
                "ai_move": ai_move,
                "ai_type": ai_type,
                "result": result
            }
        )
    else:
        # Local in-memory implementation
        game_records.append({
            "user_id": user_id,
            "timestamp": timestamp,
            "user_move": user_move,
            "ai_move": ai_move,
            "ai_type": ai_type,
            "result": result
        })
        print("Game saved:", game_records[-1])  # Debugging log

def get_game_history(user_id=None):
    """
    Retrieves game history.
    """
    if USE_DYNAMODB:
        if user_id:
            # Query for specific user in DynamoDB
            response = table.query(
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id}
            )
            return response.get("Items", [])
        else:
            # Get all records (note: inefficient for large tables)
            response = table.scan()
            return response.get("Items", [])
    else:
        # Local implementation
        if user_id:
            return [game for game in game_records if game["user_id"] == user_id]
        return game_records

def get_user_stats(user_id):
    """
    Computes win/loss/draw statistics for a user.
    """
    if USE_DYNAMODB:
        games = get_game_history(user_id)
        wins = sum(1 for g in games if g["result"] == "win")
        losses = sum(1 for g in games if g["result"] == "lose")
        draws = sum(1 for g in games if g["result"] == "draw")
        
        # Also track move distribution
        rock_count = sum(1 for game in games if game["user_move"] == "rock")
        paper_count = sum(1 for game in games if game["user_move"] == "paper")
        scissors_count = sum(1 for game in games if game["user_move"] == "scissors")
        
        return {
            "wins": wins, 
            "losses": losses, 
            "draws": draws,
            "rock": rock_count,
            "paper": paper_count,
            "scissors": scissors_count
        }
    else:
        # Local implementation
        user_games = [game for game in game_records if game["user_id"] == user_id]
        rock_count = sum(1 for game in user_games if game["user_move"] == "rock")
        paper_count = sum(1 for game in user_games if game["user_move"] == "paper")
        scissors_count = sum(1 for game in user_games if game["user_move"] == "scissors")
        
        # Also count wins/losses/draws
        wins = sum(1 for game in user_games if game["result"] == "win")
        losses = sum(1 for game in user_games if game["result"] == "lose")
        draws = sum(1 for game in user_games if game["result"] == "draw")
        
        return {
            "rock": rock_count, 
            "paper": paper_count, 
            "scissors": scissors_count,
            "wins": wins,
            "losses": losses,
            "draws": draws
        }

# Implement the other functions similarly
def get_all_users_stats():
    """
    Retrieves statistics for all users.
    """
    if USE_DYNAMODB:
        # Get all unique user IDs from DynamoDB
        response = table.scan(ProjectionExpression="user_id")
        user_ids = set(item["user_id"] for item in response.get("Items", []))
        
        # Get stats for each user
        results = []
        for user_id in user_ids:
            stats = get_user_stats(user_id)
            total_games = stats["wins"] + stats["losses"] + stats["draws"]
            win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0
            
            results.append({
                "user_id": user_id,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "draws": stats["draws"],
                "total_games": total_games,
                "win_rate": win_rate
            })
        
        return results
    else:
        # Local implementation
        user_ids = set(game["user_id"] for game in game_records)
        
        results = []
        for user_id in user_ids:
            stats = get_user_stats(user_id)
            total_games = stats["wins"] + stats["losses"] + stats["draws"]
            win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0
            
            results.append({
                "user_id": user_id,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "draws": stats["draws"],
                "total_games": total_games,
                "win_rate": win_rate
            })
        
        return results

def get_all_ai_stats():
    """
    Retrieves statistics for all AI models.
    """
    if USE_DYNAMODB:
        # Scan all records
        response = table.scan()
        games = response.get("Items", [])
        
        # Group by AI type
        ai_types = set(game["ai_type"] for game in games)
        results = []
        
        for ai_type in ai_types:
            ai_games = [g for g in games if g["ai_type"] == ai_type]
            ai_wins = sum(1 for g in ai_games if g["result"] == "lose")  # AI wins when user loses
            ai_losses = sum(1 for g in ai_games if g["result"] == "win")  # AI loses when user wins
            ai_draws = sum(1 for g in ai_games if g["result"] == "draw")
            total_games = len(ai_games)
            win_rate = (ai_wins / total_games * 100) if total_games > 0 else 0
            
            results.append({
                "ai_type": ai_type,
                "wins": ai_wins,
                "losses": ai_losses,
                "draws": ai_draws,
                "total_games": total_games,
                "win_rate": win_rate
            })
        
        return results
    else:
        # Local implementation
        ai_types = set(game["ai_type"] for game in game_records)
        results = []
        
        for ai_type in ai_types:
            ai_games = [g for g in game_records if g["ai_type"] == ai_type]
            ai_wins = sum(1 for g in ai_games if g["result"] == "lose")  # AI wins when user loses
            ai_losses = sum(1 for g in ai_games if g["result"] == "win")  # AI loses when user wins
            ai_draws = sum(1 for g in ai_games if g["result"] == "draw")
            total_games = len(ai_games)
            win_rate = (ai_wins / total_games * 100) if total_games > 0 else 0
            
            results.append({
                "ai_type": ai_type,
                "wins": ai_wins,
                "losses": ai_losses,
                "draws": ai_draws,
                "total_games": total_games,
                "win_rate": win_rate
            })
        
        return results

def get_total_games():
    """
    Returns the total number of games played.
    """
    if USE_DYNAMODB:
        response = table.scan(Select="COUNT")
        return response.get("Count", 0)
    else:
        return len(game_records)