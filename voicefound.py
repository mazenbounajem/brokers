import pyttsx3
def list_all_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        print(f"Voice: {voice.name} - ID: {voice.id}")

# Call it once to inspect:
list_all_voices()
