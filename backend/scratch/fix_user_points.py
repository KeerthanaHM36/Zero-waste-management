from app.database import SessionLocal
from app.models.user import User, RewardTransaction
from app.models.image import Image
from sqlalchemy import func

def recalculate_points():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # Sum points from RewardTransaction table
            sum_tx_points = db.query(func.sum(RewardTransaction.points)).filter(RewardTransaction.user_id == user.user_id).scalar() or 0
            
            # Count actual uploaded images
            real_image_count = db.query(Image).filter(Image.user_id == user.user_id).count()
            
            old_points = user.reward_points
            old_count = user.image_count
            
            user.reward_points = sum_tx_points
            user.image_count = real_image_count
            print(f"User {user.email}: points changed from {old_points} -> {user.reward_points}, image_count {old_count} -> {user.image_count}")
        
        db.commit()
        print("Successfully updated user points in database.")
    except Exception as e:
        db.rollback()
        print(f"Error recalculating points: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    recalculate_points()
