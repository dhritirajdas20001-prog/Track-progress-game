# Architecture Rules

These rules serve as the master context for this project. Adhere strictly to these constraints for all backend, frontend, database, and pipeline development.

## Tech Stack
- **Backend**: Python with FastAPI
- **Database**: SQLite
- **Frontend**: Pure vanilla HTML, CSS, and JavaScript (ES6+)

## Constraints & Exclusions
- **No Heavy Frameworks**: Strictly no React, Vue, Angular, or other heavy frontend frameworks.
- **No Heavy Orchestrators**: Strictly no LangChain or heavy wrapper libraries.
- **No Heavy Build Tools**: Keep frontend files simple and directly runnable in modern browsers without complex bundling steps (like Webpack/Vite unless absolutely necessary or requested).
- **Lightweight Data Pipelines**: Keep any data pipeline processing lightweight, efficient, and simple.

## Frontend Requirements
- **Progressive Web App (PWA)**: The frontend must be built as a Progressive Web App (PWA).
- **Mobile First**: Optimized specifically for mobile screens with a responsive, high-fidelity design.

## Code Standards
- **Minimalist**: Avoid bloat. Write clean, direct, and readable code.
- **High-Performance**: Prioritize speed, efficiency, and resource management.
- **Fully Typed**: Use strict typing on the backend (Python type hints, Pydantic, etc.) and JSDoc or robust TypeScript/modern JS conventions on the frontend to ensure type clarity.
