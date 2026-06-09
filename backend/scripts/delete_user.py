#!/usr/bin/env python3
"""
Delete a user and all their data from Roammate's database.

Usage:
    python backend/scripts/delete_user.py --local user@example.com
    python backend/scripts/delete_user.py --prod  user@example.com

--local  connects to the Docker Compose Postgres on localhost:5432
--prod   fetches the Railway DATABASE_PUBLIC_URL via the Railway CLI
"""

import argparse
import json
import subprocess
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

LOCAL_DSN = "postgresql://postgres:postgres@localhost:5432/roammate"

# Deletion order respects FK dependencies; CASCADE handles any stragglers.
DELETE_ORDER = [
    ("event_vote",            "user_id"),
    ("idea_vote",             "user_id"),
    ("brainstorm_bin_item",   "user_id"),
    ("brainstorm_message",    "user_id"),
    ("concierge_message",     "user_id"),
    ("google_maps_api_usage", "user_id"),
    ("token_usage",           "user_id"),
    ("usage_counter",         "user_id"),
    ("subscription_event",    "user_id"),
    ("coupon_redemption",     "user_id"),
    ("email_verification",    "user_id"),
    ("password_reset",        "user_id"),
    ("refresh_token",         "user_id"),
    ("user_identity",         "user_id"),
    # notification has both user_id and actor_id
    ("notification",          "user_id"),
    ("notification",          "actor_id"),
    ("trip_member",           "user_id"),
    # trips created by this user: cascade their children first
    ("idea_tag",              None),   # handled via idea_bin_item below
    ("idea_vote",             None),   # already done above
    ("idea_bin_item",         None),   # trip-scoped, handled via trip delete
    ("timeline_item",         None),
    ("day_route",             None),
    ("trip_day",              None),
    ("trip_member",           None),   # other members of user's trips
    ("trip",                  "created_by_id"),
    # groups owned by this user
    ("group_member",          None),   # members of owned groups
    ('"group"',               "owner_id"),
    # finally the user row itself
    ('"user"',                "id"),
]


def get_prod_dsn() -> str:
    try:
        result = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--json"],
            capture_output=True, text=True, check=True,
        )
        variables = json.loads(result.stdout)
        dsn = variables.get("DATABASE_PUBLIC_URL")
        if not dsn:
            sys.exit("ERROR: DATABASE_PUBLIC_URL not found in Railway variables.")
        return dsn
    except FileNotFoundError:
        sys.exit("ERROR: 'railway' CLI not found. Install it or run 'railway login'.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ERROR: railway CLI failed:\n{e.stderr}")


def fetch_user(cur, email: str) -> dict | None:
    cur.execute(
        'SELECT id, email, name, subscription_tier, subscription_status, created_at '
        'FROM "user" WHERE email = %s',
        (email,),
    )
    return cur.fetchone()


def delete_trips_owned_by(cur, user_id: int) -> int:
    """Delete all trips created by this user, cascading their children."""
    cur.execute('SELECT id FROM trip WHERE created_by_id = %s', (user_id,))
    trip_ids = [row["id"] for row in cur.fetchall()]
    if not trip_ids:
        return 0

    placeholders = ",".join(["%s"] * len(trip_ids))

    # Children of trip (other than those already deleted above via user_id)
    for table in ("idea_tag",):
        cur.execute(
            f'DELETE FROM {table} WHERE idea_id IN '
            f'(SELECT id FROM idea_bin_item WHERE trip_id IN ({placeholders}))',
            trip_ids,
        )
    for table in ("idea_bin_item", "timeline_item", "day_route", "trip_day",
                  "trip_member", "brainstorm_bin_item", "brainstorm_message",
                  "concierge_message", "google_maps_api_usage", "token_usage",
                  "notification"):
        cur.execute(
            f'DELETE FROM {table} WHERE trip_id IN ({placeholders})',
            trip_ids,
        )
    cur.execute(f'DELETE FROM trip WHERE id IN ({placeholders})', trip_ids)
    return len(trip_ids)


def delete_groups_owned_by(cur, user_id: int) -> int:
    cur.execute('SELECT id FROM "group" WHERE owner_id = %s', (user_id,))
    group_ids = [row["id"] for row in cur.fetchall()]
    if not group_ids:
        return 0
    placeholders = ",".join(["%s"] * len(group_ids))
    cur.execute(f'DELETE FROM group_member WHERE group_id IN ({placeholders})', group_ids)
    cur.execute(f'DELETE FROM "group" WHERE id IN ({placeholders})', group_ids)
    return len(group_ids)


def delete_user(dsn: str, email: str, env_label: str) -> None:
    conn = psycopg2.connect(dsn)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            user = fetch_user(cur, email)
            if not user:
                print(f"No user found with email '{email}' in {env_label}.")
                return

            print(f"\nFound user in {env_label}:")
            print(f"  ID:           {user['id']}")
            print(f"  Email:        {user['email']}")
            print(f"  Name:         {user['name']}")
            print(f"  Tier:         {user['subscription_tier']} / {user['subscription_status']}")
            print(f"  Created:      {user['created_at']}\n")

            confirm = input(f"Permanently delete this account and ALL associated data? [yes/N]: ").strip()
            if confirm.lower() != "yes":
                print("Aborted.")
                return

            uid = user["id"]

            # Direct user-linked rows
            for table in (
                "event_vote", "idea_vote", "brainstorm_bin_item",
                "brainstorm_message", "concierge_message",
                "google_maps_api_usage", "token_usage", "usage_counter",
                "subscription_event", "coupon_redemption",
                "email_verification", "password_reset", "refresh_token",
                "user_identity",
            ):
                cur.execute(f"DELETE FROM {table} WHERE user_id = %s", (uid,))

            # Notifications (recipient and actor)
            cur.execute("DELETE FROM notification WHERE user_id = %s OR actor_id = %s", (uid, uid))

            # Remove from other people's trips
            cur.execute("DELETE FROM trip_member WHERE user_id = %s", (uid,))

            # Trips this user created (and all their children)
            trips_deleted = delete_trips_owned_by(cur, uid)

            # Groups this user owns (and their members)
            groups_deleted = delete_groups_owned_by(cur, uid)

            # The user row itself
            cur.execute('DELETE FROM "user" WHERE id = %s', (uid,))

            conn.commit()

            print(f"\nDeleted:")
            print(f"  Trips owned:  {trips_deleted}")
            print(f"  Groups owned: {groups_deleted}")
            print(f"  User row:     {email} (id={uid})")
            print(f"\nAccount permanently removed from {env_label}.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete a Roammate user account.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prod",  action="store_true", help="Target Railway production DB")
    group.add_argument("--local", action="store_true", help="Target local Docker Compose DB")
    parser.add_argument("email", help="Email address of the account to delete")
    args = parser.parse_args()

    if args.prod:
        print("Fetching production DB credentials from Railway CLI...")
        dsn = get_prod_dsn()
        env_label = "PRODUCTION"
    else:
        dsn = LOCAL_DSN
        env_label = "LOCAL"

    delete_user(dsn, args.email, env_label)


if __name__ == "__main__":
    main()
