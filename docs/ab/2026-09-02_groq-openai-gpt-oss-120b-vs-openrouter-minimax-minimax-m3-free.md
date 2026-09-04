# Summarizer A/B — 2026-09-02

- **A** = `groq:openai/gpt-oss-120b` (free chain)
- **B** = `openrouter:minimax/minimax-m3:free` (free chain)
- Same prompt as the daemon (`SourceFetcher._summarize_youtube` + `custom_instructions.txt`), 4 videos, 1 skipped.
- Automated checks are only hints. Judge each pair on: **omit rules obeyed** (no promo, no TA, no price talk, no politics-only), **reads well aloud** (no markdown, numbers written out, no filler), **nothing important missing**.

## Scorecard

| # | Video | A words / A secs | B words / B secs | A flags | B flags |
|---|---|---|---|---|---|
| 1 | Fable 5.1 just smoked ASTRA... | 351 / 2s | 0 / 3s | clean | clean |
| 2 | Did Bessent's Treasury Buyback Spark Bitcoin's Ral | 0 / 0s | 0 / 1s | clean | clean |
| 3 | Scott Bessent’s Treasury Strategy Is Getting Serio | 96 / 1s | 73 / 5s | clean | clean |
| 4 | THE NEXT LEADER WILL BE SOCIALIST!? | 157 / 1s | 231 / 7s | clean | clean |

## 1. Fable 5.1 just smoked ASTRA...

Wes Roth · https://www.youtube.com/watch?v=GdArAq7WMSM · transcript 8,848 chars

### A — `groq:openai/gpt-oss-120b` (2.2s)

Anthropic unveiled Claude Fable version five point one alongside Mythos version five point one, though Mythos remains limited to trusted partners. The new Fable model represents a substantial advance in long‑horizon, agentic tasks and arrives with a pronounced cost reduction. By applying a memory discount to cached prompts and requiring fewer tokens to complete the same work, the model delivers output that is both cheaper and faster, and in its lower reasoning mode it outperforms Sonnet. 

The release appears timed to preempt OpenAI’s upcoming Astra model, which is expected within the next few days. Anthropic highlighted that Fable five point one achieves perfect scores on exploit benchmarks, suggesting strong cybersecurity resilience. 

In terms of usability, readability has improved markedly; research outputs are now easier to scan and understand, reducing the cognitive load for developers who work with the model extensively. Safeguards have also been refined, with binary request flags dropping by roughly sixty percent and medical‑biology fallback rates falling by about eighty‑five percent. 

Cost efficiencies are notable: low‑effort runs of Fable five point one match the performance of high‑effort Fable five at roughly one third the price, and prompt‑cache reads are four times cheaper. The model can be accessed through a cost‑optimized API command. 

Demonstrations showcased the model’s ability to generate complex interactive experiences quickly. Within ten to fifteen minutes it produced a fully voiced, isometric game reminiscent of Escape from Tarkov, complete with automatic gameplay logic, sound effects, dialogue in English and Russian, and procedurally drawn graphics generated entirely from code rather than external assets. A second iteration refined the visual detail further. 

The presenter also recreated the Stanford LM Village experiment, using multiple instances of the model to simulate a community of characters whose knowledge spreads through conversation. Each character maintains a memory stream of actions and dialogue, allowing researchers to observe information diffusion in a simulated society. 

Overall, Fable five point one delivers faster, cheaper, and more readable long‑term reasoning, enhanced safety controls, and the capacity to build sophisticated, fully voiced interactive applications in minutes, positioning it as a strong contender against upcoming competitors such as OpenAI’s Astra.

### B — `openrouter:minimax/minimax-m3:free` (2.7s)

> provider returned nothing (see fetch_debug.log)

_(empty)_

**Verdict:** [ ] A better  [ ] B better  [ ] tie — notes:

---

## 2. Did Bessent's Treasury Buyback Spark Bitcoin's Rally to $80K?

Unchained · https://www.youtube.com/watch?v=eo0vXTP-AbE · transcript 41,174 chars

### A — `groq:openai/gpt-oss-120b` (0.3s)

> provider returned nothing (see fetch_debug.log)

_(empty)_

### B — `openrouter:minimax/minimax-m3:free` (1.2s)

> provider returned nothing (see fetch_debug.log)

_(empty)_

**Verdict:** [ ] A better  [ ] B better  [ ] tie — notes:

---

## 3. Scott Bessent’s Treasury Strategy Is Getting Serious

Raoul Pal The Journey Man · https://www.youtube.com/watch?v=cv6LHADcvNA · transcript 586 chars

### A — `groq:openai/gpt-oss-120b` (0.8s)

First, the discussion highlights a shift in the United States Treasury debt market that has grown from a seemingly minor development into a significant concern. Additionally, it emphasizes that foreign investors are finding it increasingly difficult to purchase U.S. Treasury securities, prompting them to look for alternative sources of financing. Moreover, the analysis points out that hedge funds have become the primary marginal buyers filling this gap, fundamentally altering the composition of Treasury holders. Finally, the speaker suggests that this evolving dynamic underscores the importance of monitoring Treasury strategies as they become more complex and consequential.

### B — `openrouter:minimax/minimax-m3:free` (5.4s)

Scott Bessent's recent actions at the US Treasury are shaping up to be more significant than initially expected, with his focus squarely on managing America's debt situation. A core challenge is the growing difficulty of attracting foreign buyers for US debt, which has shifted the landscape considerably. With foreign demand weakening, hedge funds have stepped in as the primary marginal buyers, changing the dynamics of how Treasury debt is absorbed in the market.

**Verdict:** [ ] A better  [ ] B better  [ ] tie — notes:

---

## 4. THE NEXT LEADER WILL BE SOCIALIST!?

The Diary Of A CEO · https://www.youtube.com/watch?v=zI9okZtalGk · transcript 2,028 chars

### A — `groq:openai/gpt-oss-120b` (1.3s)

The speaker identifies artificial intelligence as the most important subject of our time and describes the current period as a golden age for the technology. He argues that the narrative focusing on a few high‑profile founders overlooks the likelihood that open‑source AI will enable entrepreneurs with no current wealth to build companies that generate massive value within the next decade. He predicts that new billionaires will emerge from such ventures, illustrating how rapid access to powerful models can democratize innovation. Contrary to common fears, the speaker points to historical evidence that technological revolutions have never caused a net decline in employment, suggesting that AI will augment rather than replace human labor. He emphasizes that AI’s capacity to accelerate scientific discovery is already reshaping biology and life‑science research, with the potential to address global challenges such as widespread hunger and curable diseases. The overall message is that AI is unlocking unprecedented opportunities for human advancement across multiple sectors.

### B — `openrouter:minimax/minimax-m3:free` (6.8s)

David Friedberg, appointed to President Trump's Council of Advisors in Science and Technology, argues that the United States as an empire is in decline and that greater government intervention historically makes services more expensive rather than more accessible. He notes that sixty-three percent of Americans live paycheck to paycheck.

On artificial intelligence, Friedberg calls AI the most important subject of our time and says the world is entering a golden age that most people do not yet recognize. He pushes back on the idea that value in AI will concentrate only among figures like Dario, Elon, and Sam. He predicts that within ten years, new billionaires will emerge from people who today have no net worth but who download open-source AI models and build companies around them, creating many such stories from people who come from nowhere.

Friedberg also disputes the narrative that AI will eliminate jobs. Drawing on data across past technological revolutions, he says there has never been a sustained decline in jobs, and he believes the average person underestimates what AI now makes possible. He points to a billion people in the world who are starving and hundreds of millions dying from curable diseases as problems AI could help resolve by expanding human capacity and transforming biology and the life sciences.

The video closes mid-sentence as Friedberg is asked whether humans will soon be able to live forever.

**Verdict:** [ ] A better  [ ] B better  [ ] tie — notes:

---

## Skipped

- GPT-6 Astra Just Went CRITICAL... — https://www.youtube.com/watch?v=qRNZMGc7TMc — no transcript (yt-dlp)
