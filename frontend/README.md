# GenAI Research Assistant Frontend

This is the frontend application for the GenAI Research Assistant - a multi-agent system for searching academic papers, performing web searches, and generating comprehensive responses to research queries.

## Integration with Backend

The frontend is now fully integrated with the backend API. Key features include:

- Chat messaging with AI models (OpenAI GPT or Google Gemini)
- Conversation history management
- Recommendations system
- Error handling and visual feedback

## Setup and Running

### Prerequisites

- Node.js 16+ installed
- Backend API running (see main project README)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Make sure the backend API is running at http://localhost:8000

3. Start the development server:

```bash
npm start
```

4. Open your browser and navigate to http://localhost:3000

## API Configuration

The frontend communicates with the backend API using the utilities in `src/utils/api.js`. 

If your backend is running on a different host or port, modify the `API_BASE_URL` in this file.

## Key Components

- **Chat Interface**: Send and receive messages with the AI assistant
- **Conversation History**: Browse and load previous conversations
- **Quick Actions**: Templates and suggestions for research queries
- **Recommendations**: AI-generated suggestions for related content

## Development

When developing, ensure both the frontend and backend are running:

1. Terminal 1 (Backend):
```bash
cd /path/to/genai-research-assistant
uvicorn app.main:app --reload
```

2. Terminal 2 (Frontend):
```bash
cd /path/to/genai-research-assistant/frontend
npm start
```

## Troubleshooting

- **CORS Issues**: If you encounter CORS errors, ensure the backend has CORS properly configured.
- **Database Errors**: The backend requires PostgreSQL. If you don't have it set up, you'll see database connection errors.
- **API Errors**: Check the error messages in the UI and the browser console for details.

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
