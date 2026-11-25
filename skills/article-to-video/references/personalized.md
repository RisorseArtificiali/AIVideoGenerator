# Personalized mode: the video with the cut of the user

Read this at Step 3 of the skill, when the user chose the personalized mode. The other steps of the skill do not change. Section 4 (the additions) also applies in the automatic mode, when the request brings content of the user or other sources.

The user wants a video with their own angle, not a summary of the article. They set the focus, they think about the cut with you, and they can add their own content or other sources. This dialogue is the only part of the work with questions. When it is over, the skill goes on to Step 4 and to the end: the storyboard is a record of what was agreed, not a request for an approval.

## Form of the dialogue

Ask one question at a time, and wait for the answer. Give your recommended answer with each question: the user can accept it with one word. Look up the facts yourself (in the source, in the project, in the documentation of the template), and ask only for decisions: they are the user's. Use a menu (AskUserQuestion) when the options are clear, and write in the language of the conversation.

If the user starts a skill of brainstorming or of grilling by name, that skill guides the form of the dialogue. The points to cover are in this file.

## 1. The focus

Ask explicitly: "On which points of the article must the video focus?" Offer the parts of the argument of the source (section 1 of `plan.md`) as the options. The user selects the points that matter, and can add a point of their own. Then ask what must stay out.

Condition: you have two lists: the points that the user wants, and the points that they do not want.

## 2. The brainstorming: how to build the video

Talk with the user, one question at a time. For each point, propose your recommendation with its reason. The points:

- **The viewer.** Who is the video for, and what does that viewer already know?
- **The angle.** What does the user think of the article? Which idea do they want the viewer to take away? Where do they agree, doubt, or have experience? This is the cut of the video. It shows in the opening, in the order of the chapters, and in the conclusion.
- **The structure.** Which point opens the video, in which order the chapters go, and what closes the video.
- **The length.** The coverage of the menu (full or short) can change here.
- **The additions.** The content of the user and the external sources (section 4).

Condition: the five points are decided, and the user accepts the cut of the video as you state it in two sentences.

## 3. The grill me: the check of the plan

Show the plan in a table: chapter, point of the source or addition, number of beats. Then question the user on it, one question at a time, until no question is open. Cover at least:

- **Inclusion.** Each point that the user chose has a chapter or a beat. Each piece of their content is in the place that serves it best.
- **The cut.** Is the angle visible in the opening and in the conclusion? Is there a chapter that still reads as a summary of the article, without the view of the user?
- **The proportions.** The main article is the focus. The beats from the external sources are few.
- **The truth.** Each number and each claim of the additions has a source. A doubt of yours on a number or a claim of the user is said here.
- **The limits.** What the user accepts to leave out. The length.

When an answer changes the plan, change the table and ask again on that part.

Condition: the user confirms that the plan includes everything that they wanted and has their cut.

## 4. The additions

### The content of the user

Text or reasoning of the user that integrates the article: an example, an explanation, an opinion, an experience.

- Save it in `build/source/user-notes.md`: the text that the user gives, or a summary of what they said in the dialogue, with their words where their words matter.
- Integrate it as a part of the narration, in the place that serves it best. Write "content of the user" in the visual note of those beats: `script.md` and `storyboard.md` then show where it is.
- It goes in the video as the user gives it, and it is their video: the screen does not label it. If you doubt a number or a claim of the user, say it in the grill me (section 3) and follow the decision of the user. In the automatic mode there is no dialogue: the video shows it as the user gives it, and the report says the doubt.

### The external sources

- An external source enriches a point of the article: an example, a number, a consequence, a different view. Read it as in Step 2 of the skill, and save it in `build/source/`.
- It is a light enrichment: a few beats in all, inside the chapters of the article. An external source does not get a chapter. The focus of the video stays the main article.
- The rules for the content of the skill apply to it: the source of a quotation on the screen, a rumor stays a rumor, a number read from a figure has a note.

Condition: each addition is saved in `build/source/` and has its place in the plan.

## 5. The plan

Go back to Step 3 of the skill. Plan the chapters and write `narration.py` as `plan.md` says, following the agreed plan. Then write `storyboard.md`: the chapters, the beats, the duration, and for each chapter its point (the source, the content of the user, an external source). Continue with Step 4 of the skill.
