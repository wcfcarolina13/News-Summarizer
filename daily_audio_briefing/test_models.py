import os
import google.generativeai as genai

key = open('.env').read().strip().split('=')[1]
genai.configure(api_key=key)

test_names = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]

for name in test_names:
    try:
        model = genai.GenerativeModel(name)
        resp = model.generate_content("Say OK")
        print("OK: " + name)
    except Exception as e:
        print("FAIL: " + name + " - " + str(e)[:100])
