#!/usr/bin/env python3
"""Test script for email notifications."""

import os
import sys
import yaml

sys.path.insert(0, "src")

from bayesian_sprinkler.notifier import send_email_alert


def test_mail():
    config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml") as f:
            config = yaml.safe_load(f)

    sender = os.environ.get("EMAIL_SENDER") or config.get("email", {}).get("sender")
    password = os.environ.get("EMAIL_PASSWORD") or config.get("email", {}).get("password")
    recipient = os.environ.get("EMAIL_RECIPIENT") or config.get("email", {}).get("recipient") or sender

    if not sender or not password:
        print("ERROR: Email not configured.")
        print("Set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT env vars")
        print("Or fill in config.yaml and ensure config.yaml is loaded.")
        sys.exit(1)

    print(f"Testing email notification...")
    print(f"  From: {sender}")
    print(f"  To:   {recipient}")

    config["email"] = config.get("email", {})
    config["email"]["sender"] = sender
    config["email"]["password"] = password
    config["email"]["recipient"] = recipient

    success = send_email_alert(
        config,
        subject="SmartSprinkler: Test Email",
        body="This is a test email from SmartSprinkler.\n\nIf you receive this, the email alert system is working correctly.",
    )

    if success:
        print("\nEmail sent successfully!")
    else:
        print("\nFailed to send email. Check logs above.")
        sys.exit(1)
