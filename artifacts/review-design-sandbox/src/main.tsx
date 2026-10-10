import { createRoot } from 'react-dom/client';

import App from './App';
import StudioSession from './StudioSession';

import './index.css';

createRoot(document.getElementById('root')!).render(<StudioSession><App /></StudioSession>);
