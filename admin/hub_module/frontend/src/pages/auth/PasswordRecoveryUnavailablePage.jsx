import { Link } from 'react-router-dom';

function PasswordRecoveryUnavailablePage() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="card max-w-md w-full p-6 text-center">
        <h1 className="text-2xl font-bold text-gold-400">Password recovery unavailable</h1>
        <p className="mt-3 text-navy-300">
          Self-service password recovery is not configured. Contact your WaddleBot administrator
          to regain access.
        </p>
        <Link to="/login" className="inline-block mt-6 text-sky-400 hover:text-sky-300">
          Return to sign in
        </Link>
      </div>
    </div>
  );
}

export default PasswordRecoveryUnavailablePage;
