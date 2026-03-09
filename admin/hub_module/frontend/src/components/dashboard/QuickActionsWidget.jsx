import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

function QuickActionsWidget({ id }) {
  const links = [
    { label: 'Submit Support Ticket', to: `/community/${id}/support/submit` },
    { label: 'My Support Tickets', to: `/community/${id}/support/my-tickets` },
  ];
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="font-semibold text-sky-100">Quick Actions</h2>
      </div>
      <div className="p-2">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="block px-4 py-2 text-sm text-navy-300 hover:bg-navy-800 hover:text-sky-300 rounded-lg transition-colors"
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

QuickActionsWidget.propTypes = {
  id: PropTypes.string.isRequired,
};

export default QuickActionsWidget;
