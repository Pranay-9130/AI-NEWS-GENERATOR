# Ethical AI News Generator - Project Documentation

## 1. Abstract
The **Ethical AI News Generator** is a web-based application designed to bridge the gap between rapid information dissemination and journalistic integrity. By leveraging the **Gemini-1.5-Flash** large language model, the system generates news articles on user-specified topics while adhering to strict ethical guidelines and customizable moderation levels. For visual assets, it integrates with the **Hugging Face** inference API (e.g. Stable Diffusion) so that images can be generated based on the same topic. The project demonstrates a practical application of AI in media, focusing on reducing bias and ensuring content safety through automated moderation presets....

## 2. Introduction
In the digital age, the demand for real-time news coverage often conflicts with the need for thorough fact-checking and ethical reporting. Artificial Intelligence offers a solution to this challenge by automating content creation; however, uncontrolled AI generation can lead to the spread of misinformation or toxic content. This project introduces an "Ethical-First" approach to AI journalism, providing a platform where news generation is governed by ethical prompts and safety filters.

## 3. Problem Statement
The current news ecosystem faces several critical challenges:
- **Misinformation:** Rapidly generated content often lacks verification, leading to the viral spread of false data.
- **Harmful Bias:** AI models can unintentionally produce content that is biased, offensive, or insensitive.
- **Complexity of Moderation:** Manually screening news content for ethical compliance is time-consuming and prone to human error.
- **Accessibility:** Small news outlets often lack the resources to maintain high-speed coverage while ensuring strict editorial standards.

## 4. Proposed Solution
The proposed solution is a **Flask-based web application** integrated with **Google's Gemini Pro** (Gemini-1.5-Flash) API. 
Key features include:
- **Ethical Prompt Engineering:** The system uses specific prompt templates that instruct the AI to prioritize neutrality, factual accuracy, and sensitivity.
- **Dynamic Moderation Levels:** Users can select between different moderation intensities (e.g., Low, Moderate, High) which adjust the AI's constraints on content tone and safety.
- **Multi‑API Support:** The backend uses Google Gemini for text/article generation while images are produced via the Hugging Face Inference API (Stable Diffusion). This allows specialized handling of content and media.
- **Interactive UI:** A modern, responsive interface built with HTML/CSS and JavaScript (Glassmorphism design) for seamless user interaction.
- **Fast Content Generation:** Utilizing the Flash model to provide near-instantaneous article generation without sacrificing quality.

## 5. Objectives
The primary objectives of the Ethical AI News Generator are:
- **To promote Ethical AI usage:** Demonstrate how AI can be explicitly programmed to follow journalistic ethics.
- **To automate content moderation:** Reduce the burden of manual oversight by embedding moderation directly into the generation process.
- **To provide customizable safety:** Allow users/editors to control the "strictness" of content generation based on their platform's requirements.
- **To showcase modern web architecture:** Implement a clean, modular full-stack application using Python (Flask) and modern frontend techniques.
- **To ensure performance and scalability:** Use lightweight models (Gemini-1.5-Flash) to ensure the application remains fast and cost-effective.
