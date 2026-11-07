"""Polite, time-aware Japanese greetings for the character-free core."""

GREETING_GROUPS = {
    'morning': (
        ('morning_1', 'おはようございます。今日は何についてお話ししましょうか。'),
        ('morning_2', 'おはようございます。日本語で会話を始めましょう。'),
        ('morning_3', 'おはようございます。今日はどんなことを練習しますか。'),
        ('morning_4', 'おはようございます。ご希望の話題を教えてください。'),
    ),
    'afternoon': (
        ('afternoon_1', 'こんにちは。今日は何についてお話ししましょうか。'),
        ('afternoon_2', 'こんにちは。日本語の会話を練習しましょう。'),
        ('afternoon_3', 'こんにちは。練習したい話題はありますか。'),
        ('afternoon_4', 'こんにちは。自由にお話しください。'),
    ),
    'evening': (
        ('evening_1', 'こんばんは。今日は何についてお話ししましょうか。'),
        ('evening_2', 'こんばんは。日本語で会話を練習しましょう。'),
        ('evening_3', 'こんばんは。今日の出来事についてお話ししますか。'),
        ('evening_4', 'こんばんは。話したいことを教えてください。'),
    ),
    'night': (
        ('night_1', 'こんばんは。少し日本語でお話ししましょうか。'),
        ('night_2', 'こんばんは。ご希望の話題を教えてください。'),
        ('night_3', 'こんばんは。今日はどんな練習をしましょうか。'),
        ('night_4', 'こんばんは。日本語の会話を始めましょう。'),
    ),
}
GREETING_BY_ID = {identity: phrase for entries in GREETING_GROUPS.values() for identity, phrase in entries}
