# VectorShift Integrations Technical Assessment

## Overview

This project is a full-stack integration assessment for VectorShift, demonstrating the implementation of a HubSpot OAuth integration using FastAPI (Python) for the backend and React (JavaScript) for the frontend. The project also includes minimal UI/UX and supports loading data from HubSpot after authentication.

---

## Assessment Requirements

- **Part 1:** Implement HubSpot OAuth integration (backend and frontend)
- **Part 2:** Load HubSpot items (contacts, companies, deals) and display them in the frontend
- Use FastAPI for backend, React for frontend
- Use Redis for temporary storage of OAuth state and credentials
- UI should allow connecting to HubSpot and loading data

---

## My Approach & Thinking Process

1. **Understand the Reference Integrations:**
   - Studied `airtable.py` and `notion.py` to understand the OAuth flow, credential storage, and item loading pattern.
2. **Plan the Workflow:**
   - Implement backend OAuth endpoints and data loading for HubSpot, mirroring the structure of Airtable/Notion.
   - Implement frontend integration component for HubSpot, matching the UI/UX of existing integrations.
   - Ensure the UI is minimal, modern, and user-friendly.
3. **Implement Step by Step:**
   - Backend: Implemented `authorize_hubspot`, `oauth2callback_hubspot`, `get_hubspot_credentials`, and `get_items_hubspot`.
   - Frontend: Created `hubspot.js` integration, updated integration selection, and ensured data loading is visible in the UI.
   - Debugged and iterated based on test results and UI feedback.

---

## Backend Implementation (FastAPI)

- **OAuth Flow:**
  - `authorize_hubspot`: Generates the HubSpot OAuth URL, stores state and PKCE verifier in Redis.
  - `oauth2callback_hubspot`: Handles the callback, exchanges code for tokens, stores credentials in Redis.
  - `get_hubspot_credentials`: Retrieves and deletes credentials from Redis for one-time use.
- **Data Loading:**
  - `get_items_hubspot`: Uses the access token to fetch contacts, companies, and deals from HubSpot's API. Returns a list of dicts for frontend consumption.
- **Endpoints:**
  - `/integrations/hubspot/authorize` (POST)
  - `/integrations/hubspot/oauth2callback` (GET)
  - `/integrations/hubspot/credentials` (POST)
  - `/integrations/hubspot/load` (POST)
- **Logic:**
  - All sensitive state and credentials are stored in Redis with expiration for security.
  - Data returned is always JSON serializable.

---

## Frontend Implementation (React)

- **Integration Selection:**
  - User can select Notion, Airtable, or HubSpot from a dropdown.
- **HubSpot Integration Component:**
  - Handles OAuth connect flow in a popup window.
  - After successful connection, stores credentials in state.
- **Data Loading:**
  - After connecting, user can click "Load Data" to fetch and display HubSpot items as formatted JSON.
- **UI/UX:**
  - Minimal, modern, and easy to use.
  - All logic is commented for clarity.

---

## Code Structure & Comments

- All major files and functions are commented to explain logic and reasoning.
- Comments describe the OAuth flow, data fetching, and UI state management.
- See `backend/integrations/hubspot.py`, `frontend/src/integrations/hubspot.js`, `frontend/src/integration-form.js`, and `frontend/src/data-form.js` for detailed comments.

---

## How to Run the Project

### 1. **Start Redis**

```
redis-server
```

### 2. **Backend (FastAPI)**

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. **Frontend (React)**

```
cd frontend
npm install
npm start
```

### 4. **Connect to HubSpot**

- Open [http://localhost:3000](http://localhost:3000)
- Select "HubSpot" from the integration dropdown
- Click "Connect to HubSpot" and complete the OAuth flow
- Click "Load Data" to fetch and display HubSpot items

---

## Troubleshooting

- If "Load Data" returns nothing, make sure your HubSpot account has contacts/companies/deals.
- If OAuth fails, check your HubSpot app's redirect URI and scopes.
- If credentials expire, reconnect and try again.

---

## Credits

- Assessment and starter code by VectorShift
- Implementation and documentation by Devashish

---

For questions, reach out to recruiting@vectorshift.ai
