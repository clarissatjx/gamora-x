import RailPage from './pages/RailPage';

// Phase 0 prototype: Rail only, no router/sidebar yet. Once this split is validated,
// Door/ACV/SHM pages and the sidebar shell follow the same pattern.
export default function App() {
  return (
    <div>
      <div className="gx-topbar">
        <div className="gx-crumb">gamora-x / webapp / rail</div>
        <div className="gx-brand">
          <div className="gx-mark">g</div>
          <div className="gx-name">gamora · CdM</div>
        </div>
      </div>
      <div className="gx-shell">
        <RailPage />
      </div>
    </div>
  );
}
