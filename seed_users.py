"""
Seed script to populate the database with diverse user profiles for testing the matching system.
Run this script with: python seed_users.py
"""
import os
import sys
from datetime import datetime
from sqlalchemy.orm import Session
from app import app, db
from models.users import User
from models.profiles import Profile
from utils.embeddings import generate_profile_embedding
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diverse test user profiles
SEED_USERS = [
    {
        "id": "seed_user_001",
        "name": "Alex Rivera",
        "email": "alex.rivera@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
        "profile": {
            "age": 28,
            "gender": "Male",
            "height": 180,
            "bio": "Adventure seeker and coffee enthusiast. Love hiking on weekends and trying new cuisines. Always up for a spontaneous road trip or deep conversations about life.",
            "interests": "🏔 Hiking, ☕ Coffee, 🌍 Travel, 📚 Reading, 🎵 Indie Music",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_002",
        "name": "Maya Johnson",
        "email": "maya.johnson@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop",
        "profile": {
            "age": 26,
            "gender": "Female",
            "height": 165,
            "bio": "Yoga instructor by day, bookworm by night. Plant mom to 15 beautiful babies. Looking for someone who appreciates good coffee and deep conversations.",
            "interests": "🧘 Yoga, 📖 Books, 🌱 Plants, ☕ Coffee, 🎨 Art",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_003",
        "name": "David Chen",
        "email": "david.chen@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop",
        "profile": {
            "age": 30,
            "gender": "Male",
            "height": 175,
            "bio": "Software engineer who loves building things. Weekend warrior at the gym. Huge fan of sci-fi movies and tech podcasts. Let's grab coffee and talk about the future!",
            "interests": "💻 Tech, 🏋️ Fitness, 🎬 Sci-Fi Movies, 🎮 Gaming, 🎧 Podcasts",
            "location": "Mombasa",
            "photos": [
                "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_004",
        "name": "Sophie Williams",
        "email": "sophie.williams@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop",
        "profile": {
            "age": 27,
            "gender": "Female",
            "height": 168,
            "bio": "Marketing professional with a passion for photography. Love exploring new restaurants and capturing beautiful moments. Believer in living life to the fullest!",
            "interests": "📸 Photography, 🍜 Foodie, ✈️ Travel, 🎨 Art Galleries, 🌅 Sunsets",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_005",
        "name": "Marcus Thompson",
        "email": "marcus.thompson@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop",
        "profile": {
            "age": 29,
            "gender": "Male",
            "height": 185,
            "bio": "Professional chef who loves experimenting with fusion cuisine. Basketball enthusiast and music lover. Looking for someone to share amazing food experiences with.",
            "interests": "🍳 Cooking, 🏀 Basketball, 🎵 Music, 🍷 Wine, 🌶️ Spicy Food",
            "location": "Kisumu",
            "photos": [
                "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1507081323647-4d250478b919?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_006",
        "name": "Elena Martinez",
        "email": "elena.martinez@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=400&h=400&fit=crop",
        "profile": {
            "age": 25,
            "gender": "Female",
            "height": 162,
            "bio": "Dance teacher and fitness enthusiast. Love salsa, bachata, and all things Latin music. Adventurous spirit looking for a partner in crime for spontaneous adventures!",
            "interests": "💃 Dancing, 🎶 Latin Music, 🏃 Running, ✈️ Travel, 🌮 Mexican Food",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_007",
        "name": "James Anderson",
        "email": "james.anderson@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop",
        "profile": {
            "age": 31,
            "gender": "Male",
            "height": 178,
            "bio": "Environmental scientist passionate about sustainability. Weekend hiker and nature photographer. Seeking someone who cares about making the world a better place.",
            "interests": "🌍 Sustainability, 🏔️ Hiking, 📸 Photography, 🌱 Nature, 📚 Science",
            "location": "Nakuru",
            "photos": [
                "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_008",
        "name": "Zara Ahmed",
        "email": "zara.ahmed@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=400&h=400&fit=crop",
        "profile": {
            "age": 24,
            "gender": "Female",
            "height": 170,
            "bio": "Graphic designer with a love for all things creative. Coffee addict and cat lover. Always sketching something new. Looking for someone artistic and fun!",
            "interests": "🎨 Design, ☕ Coffee, 🐱 Cats, ✏️ Drawing, 🎭 Theater",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_009",
        "name": "Ryan O'Connor",
        "email": "ryan.oconnor@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?w=400&h=400&fit=crop",
        "profile": {
            "age": 32,
            "gender": "Male",
            "height": 182,
            "bio": "Entrepreneur and travel junkie. Have visited 30+ countries and counting. Love trying extreme sports and new experiences. Seeking an adventurous partner!",
            "interests": "✈️ Travel, 🪂 Skydiving, 🏄 Surfing, 💼 Business, 🍣 Sushi",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_010",
        "name": "Priya Patel",
        "email": "priya.patel@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=400&h=400&fit=crop",
        "profile": {
            "age": 26,
            "gender": "Female",
            "height": 163,
            "bio": "Doctor by profession, foodie by passion. Love exploring different cultures through their cuisine. Yoga practitioner and meditation enthusiast. Seeking genuine connections.",
            "interests": "🏥 Medicine, 🍜 Food, 🧘 Yoga, 📚 Reading, 🌸 Meditation",
            "location": "Eldoret",
            "photos": [
                "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_011",
        "name": "Lucas Brown",
        "email": "lucas.brown@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=400&h=400&fit=crop",
        "profile": {
            "age": 28,
            "gender": "Male",
            "height": 176,
            "bio": "Music producer and DJ. Live for festivals and electronic music. Dog dad to a golden retriever. Looking for someone who loves music and good vibes!",
            "interests": "🎧 Music Production, 🎵 EDM, 🐕 Dogs, 🎪 Festivals, 🎹 Piano",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1500259571355-332da5cb07aa?w=400&h=400&fit=crop"
            ]
        }
    },
    {
        "id": "seed_user_012",
        "name": "Isabella Santos",
        "email": "isabella.santos@test.com",
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop",
        "profile": {
            "age": 27,
            "gender": "Female",
            "height": 167,
            "bio": "Fashion blogger and style enthusiast. Love brunch dates and exploring vintage shops. Passionate about sustainable fashion. Looking for someone stylish and fun!",
            "interests": "👗 Fashion, 📷 Instagram, 🥂 Brunch, ♻️ Sustainability, 🛍️ Shopping",
            "location": "Nairobi",
            "photos": [
                "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop",
                "https://images.unsplash.com/photo-1509967419530-da38b4704bc6?w=400&h=400&fit=crop"
            ]
        }
    }
]


def seed_database():
    """Populate database with seed users"""
    with app.app_context():
        logger.info("Starting database seeding...")
        
        # Check if seed users already exist
        existing_users = User.query.filter(User.id.like('seed_user_%')).count()
        if existing_users > 0:
            logger.warning(f"Found {existing_users} existing seed users. Cleaning up...")
            # Delete existing seed data
            Profile.query.filter(Profile.user_id.like('seed_user_%')).delete()
            User.query.filter(User.id.like('seed_user_%')).delete()
            db.session.commit()
            logger.info("Cleanup complete.")
        
        success_count = 0
        error_count = 0
        
        for user_data in SEED_USERS:
            try:
                # Create user
                user = User(
                    id=user_data["id"],
                    name=user_data["name"],
                    email=user_data["email"],
                    avatar_url=user_data["avatar_url"]
                )
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Create profile
                profile_data = user_data["profile"]
                profile = Profile(
                    user_id=user.id,
                    age=profile_data["age"],
                    gender=profile_data["gender"],
                    height=profile_data.get("height"),
                    bio=profile_data["bio"],
                    interests=profile_data["interests"],
                    location=profile_data["location"],
                    photos=profile_data["photos"]
                )
                
                # Generate embedding
                logger.info(f"Generating embedding for {user.name}...")
                embedding = generate_profile_embedding(
                    bio=profile.bio,
                    interests=profile.interests
                )
                
                if embedding:
                    profile.embedding = embedding
                    logger.info(f"✓ Generated embedding with {len(embedding)} dimensions for {user.name}")
                else:
                    logger.warning(f"✗ Failed to generate embedding for {user.name}")
                
                db.session.add(profile)
                db.session.commit()
                
                success_count += 1
                logger.info(f"✓ Created user: {user.name} ({user.id})")
                
            except Exception as e:
                db.session.rollback()
                error_count += 1
                logger.error(f"✗ Error creating user {user_data['name']}: {str(e)}")
        
        logger.info("\n" + "="*60)
        logger.info("SEEDING COMPLETE!")
        logger.info(f"Successfully created: {success_count} users")
        logger.info(f"Errors: {error_count}")
        logger.info("="*60)
        
        # Display summary
        total_users = User.query.count()
        total_profiles = Profile.query.count()
        profiles_with_embeddings = Profile.query.filter(Profile.embedding.isnot(None)).count()
        
        logger.info(f"\nDatabase Summary:")
        logger.info(f"  Total Users: {total_users}")
        logger.info(f"  Total Profiles: {total_profiles}")
        logger.info(f"  Profiles with Embeddings: {profiles_with_embeddings}")
        logger.info("\n✨ Your matching system is ready to test!")


if __name__ == "__main__":
    seed_database()
