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

The study involved 21 participants and 21 video recordings. The recordings provided the basis for extracting behavioral data, which was combined with survey responses. The original plan was to use interaction logs from the application, but the application did not produce those logs. Instead, I had to work with Zoom screen recordings, webcam footage, and available automatic transcripts. This changed my project from a conventional data analysis task into a video processing and feature extraction problem.

The first challenge was recovering the recordings from a damaged archive. Standard extraction tools could not read the archive correctly because its central directory was corrupted. I developed a Python script that searched for local ZIP file headers and recovered accessible video and transcript entries. This allowed the analysis to proceed without relying on the damaged archive index.

After recovering the available files, I developed a segmentation pipeline to identify the different stages of the learning experience. I used timestamps from narration in the transcripts and visual information from video frames sampled at one frame per second. The program divided sessions into lessons, quizzes, the survival phone call, navigation, and the post-session interview. I also handled unusual cases such as an application restart, incomplete transcripts, and repeated survival attempts. Missing observations were kept separate from actual zero values.

Once the sessions were segmented, I extracted features that represented different aspects of participant behavior. These included total session duration, time spent in each lesson, navigation duration, number of survival attempts, quiz feedback, participant speech, and webcam movement. I stored these measurements in CSV files using participant identifiers instead of names. This made the information easier to analyze and helped protect participant privacy.

![Shelter-seeking task with on-screen navigation signs and controls](report_figures/session_p09_survival_nav.png)

*Figure 3. Shelter-seeking task with on-screen navigation signs and controls.*

Another important part of my project was computer vision. I used MediaPipe FaceLandmarker [3] to estimate head orientation and facial action units [1] from the webcam overlay. Head orientation included yaw, pitch, and roll. I calculated how often a participant's head position deviated from their own typical position as an approximate measure of looking away. Using an individual baseline helped reduce the effect of differences in camera placement and sitting position.

The facial features included brow movement, blinking, frowning, mouth stretching, and jaw movement. These were numerical estimates rather than direct measurements of emotions. Because the webcam images were small and sometimes unavailable, I treated facial measurements as noisy behavioral indicators. A frown alone does not prove that someone is confused, and head orientation is not the same as eye tracking.

To examine how these signals changed over time, I compared facial action-unit activation across six example sessions. The graph shows 15-second averages of frowning, brow raising, smiling, and jaw opening. The patterns vary across participants and recording phases, illustrating why individual behavior and recording context must be considered when interpreting these measurements. The signals do not directly establish a participant's emotional state.

![Facial action-unit activation across six example sessions (P02, P05, P08, P12, P14, and P21), using 15-second averages](figures/expr_across_sessions.png)

*Figure 4. Facial action-unit activation across six example sessions (P02, P05, P08, P12, P14, and P21), using 15-second averages.*

I then combined the extracted features with survey measures of engagement, effort, confusion, and knowledge [5]. Pre-test and post-test scores allowed me to examine learning outcomes. I used Spearman correlation [7] to explore relationships between behavior and survey responses, because it measures the strength of a monotonic relationship without requiring a linear relationship.

The existing analysis showed several interesting patterns. Looking away more frequently was