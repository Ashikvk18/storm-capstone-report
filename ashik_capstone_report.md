# STORM: Identifying Explainable Behavioral Indicators of Engagement and Confusion in Virtual Reality Learning Environments

*Ashik Dey Rupak | Computer Science Capstone | Truman State University*

## Abstract

This capstone project investigates which explainable behavioral features are indicative of cognitive engagement and confusion in immersive virtual reality (IVR) learning environments. The study uses STORM, a Unity-based VR program that teaches tornado formation, geography, and shelter-seeking behavior. Although the original research plan assumed the application would produce interaction logs, no in-app telemetry was recorded; the behavioral record instead consisted of Zoom screen recordings, webcam footage, and automatic transcripts from 21 participants. I built a complete analysis pipeline to recover the recordings from a damaged archive, segment sessions into learning phases, and extract interpretable features including phase timing, survival attempts, webcam motion, head pose, and facial action units estimated with MediaPipe. Survey-based composites of engagement, effort, confusion, and knowledge served as labels. Correlational analysis identified several exploratory associations — longer first-lesson dwell time predicted higher post-test scores, looking away predicted lower reported effort, and frowning and mouth-stretch activation co-occurred with reported confusion — while predictive modeling honestly failed to beat the mean baseline at this sample size. The project contributes a feasible video-derived behavioral measurement pipeline and preliminary, hypothesis-generating indicators for future instrumented VR learning studies.

## 1. Detailed Description of My Capstone Experience

For my capstone project, I worked on STORM, an interactive learning program developed in Unity that teaches users how tornadoes form, where they commonly occur, and how to respond safely during a tornado. The program combines educational lessons, quizzes, and a simulated emergency in which the participant must navigate to a shelter. Our goal was to understand how people learn and behave while interacting with this environment.

![STORM geography lesson showing the interactive map of the United States](report_figures/session_p14_lesson2.png)

*Figure 1. STORM geography lesson showing the interactive map of the United States.*

I worked with my project partner, Shalin Bhattarai, and we focused on different research questions. My research question (RQ2) was: Which explainable behavioral features are indicative of cognitive engagement and confusion in immersive VR learning environments [4, 6]? I wanted to determine whether observable behaviors, such as time spent on lessons, navigation difficulties, head movement, and facial expressions, could provide useful information about a learner's experience.

![Example of an in-app multiple-choice knowledge question](report_figures/session_p05_quiz1.png)

*Figure 2. Example of an in-app multiple-choice knowledge question.*

The study involved 21 participants and 21 video recordings. The recordings provided the basis for extracting behavioral data, which was combined with survey responses. The original plan was to use interaction logs from the application, but the application did not produce those logs. Instead, I had to work with Zoom screen recordings, webcam footage, and available automatic transcripts.