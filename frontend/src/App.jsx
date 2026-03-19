// /**
//  * App.jsx
//  * Root component — routing, auth guard, global reset styles.
//  */

// import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
// import { AuthProvider, useAuth } from "./context/AuthContext";
// import Login     from "./pages/Login";
// import Dashboard from "./pages/Dashboard";
// import Footer from "./components/Footer";  

// // ── Protected route wrapper ───────────────────────────────────────────────────
// function PrivateRoute({ children }) {
//   const { isLoggedIn } = useAuth();
//   return isLoggedIn ? children : <Navigate to="/login" replace />;
// }

// // ── Public route (redirect if already logged in) ──────────────────────────────
// function PublicRoute({ children }) {
//   const { isLoggedIn } = useAuth();
//   return isLoggedIn ? <Navigate to="/dashboard" replace /> : children;
// }

// // ── Keyframe injection (can't use CSS files in this setup easily) ─────────────
// const globalCSS = `
//   *, *::before, *::after { box-sizing: border-box; }
//   html, body { margin: 0; padding: 0; }
//   body { background: #080c14; }
//   input[type=number]::-webkit-inner-spin-button,
//   input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
//   input[type=number] { -moz-appearance: textfield; }
//   @keyframes spin { to { transform: rotate(360deg); } }
//   ::-webkit-scrollbar { width: 6px; }
//   ::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
//   ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
//   ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }
// `;

// export default function App() {
//   return (
//     <>
//       <style>{globalCSS}</style>
//       <AuthProvider>
//         <BrowserRouter>
//           <Routes>
//             <Route path="/"          element={<Navigate to="/dashboard" replace />} />
//             <Route path="/login"     element={<PublicRoute><Login /></PublicRoute>} />
//             <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
//             <Route path="*"          element={<Navigate to="/dashboard" replace />} />
//           </Routes>
//           </div>
//            <Footer />   {/* ← add this */}
//           </div>
//         </BrowserRouter>
//       </AuthProvider>
//     </>
//   );
// }


/**
 * App.jsx
 * Root component — routing, auth guard, global reset styles.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login     from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Footer    from "./components/Footer";

function PrivateRoute({ children }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

function PublicRoute({ children }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? <Navigate to="/dashboard" replace /> : children;
}

const globalCSS = `
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: #080c14; }
  input[type=number]::-webkit-inner-spin-button,
  input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  input[type=number] { -moz-appearance: textfield; }
  @keyframes spin { to { transform: rotate(360deg); } }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }
`;

export default function App() {
  return (
    <>
      <style>{globalCSS}</style>
      <AuthProvider>
        <BrowserRouter>
          <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
            <div style={{ flex: 1 }}>
              <Routes>
                <Route path="/"          element={<Navigate to="/dashboard" replace />} />
                <Route path="/login"     element={<PublicRoute><Login /></PublicRoute>} />
                <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
                <Route path="*"          element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </div>
            <Footer />
          </div>
        </BrowserRouter>
      </AuthProvider>
    </>
  );
}