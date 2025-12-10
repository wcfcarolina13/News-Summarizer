# Custom Instructions for Personalized Summaries

## Overview
You can now customize how video summaries are generated based on your interests and preferences.

## How to Use

### Option 1: GUI (Recommended)
1. Launch the Daily Audio Briefing app
2. Click the **"Custom Instructions"** button (next to "Edit Sources")
3. Enter your custom instructions in the text box
4. Click **"Save Instructions"**

### Option 2: Manual File Edit
Edit the `custom_instructions.txt` file directly in the `daily_audio_briefing` folder.

## Example Instructions

```
I'm a crypto investor and AI researcher interested in Bitcoin, Ethereum, DeFi, and machine learning.

Focus on:
- Main points, takeaways, and unique insights ("alpha")
- Specific price predictions, technical levels, and data points
- Companies, projects, or protocols mentioned (with brief context)
- Contrarian views or novel analysis
- Actionable recommendations

Organize summaries to highlight information most relevant to my interests.
```

## Tips

- **Be specific about your interests**: Mention specific topics, industries, or areas of focus
- **Define what matters to you**: Specify if you want price levels, technical details, company mentions, etc.
- **Set your role/context**: "I'm a trader", "I'm an investor", "I'm a researcher" helps the AI understand your perspective
- **Request specific formats**: Ask for lists of companies/projects, key takeaways, actionable insights, etc.

## How It Works

Your custom instructions are added to the AI prompt when generating summaries from video transcripts. The AI will:
1. Apply all standard summarization rules (deduplication, comprehensive coverage, etc.)
2. Additionally consider your personal context and interests
3. Emphasize and organize information based on your preferences

## File Location

`/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/custom_instructions.txt`

Leave the file empty or delete it to use default summarization behavior.
