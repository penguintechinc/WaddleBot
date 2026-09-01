/**
 * Calendar Admin Routes
 * Community admin calendar event CRUD, RSVPs, ticketing, check-in, attendance, event admins.
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { proxyToCalendar, buildUserContext } from '../utils/calendarProxy.js';
import * as ticketController from '../controllers/ticketController.js';

const router = Router({ mergeParams: true });
router.use(requireAuth);

// ---------------------------------------------------------------------------
// Calendar Events CRUD
// ---------------------------------------------------------------------------

router.get('/:communityId/calendar/events', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId } = req.params;
    const queryParams = new URLSearchParams();
    if (req.query.status) queryParams.set('status', req.query.status);
    if (req.query.category) queryParams.set('category', req.query.category);
    if (req.query.limit) queryParams.set('limit', req.query.limit);
    if (req.query.offset) queryParams.set('offset', req.query.offset);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.post('/:communityId/calendar/events', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events`, {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.status(201).json(data);
  } catch (err) { next(err); }
});

router.get('/:communityId/calendar/events/:eventId', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.put('/:communityId/calendar/events/:eventId', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}`, {
      method: 'PUT',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.delete('/:communityId/calendar/events/:eventId', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

// ---------------------------------------------------------------------------
// Event Approval
// ---------------------------------------------------------------------------

router.post('/:communityId/calendar/events/:eventId/approve', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/approve`, {
      method: 'POST',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.post('/:communityId/calendar/events/:eventId/reject', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/reject`, {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

// ---------------------------------------------------------------------------
// RSVPs
// ---------------------------------------------------------------------------

router.post('/:communityId/calendar/events/:eventId/rsvp', async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/rsvp`, {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.delete('/:communityId/calendar/events/:eventId/rsvp', async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/rsvp`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.get('/:communityId/calendar/events/:eventId/attendees', requireCommunityAdmin, async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/attendees`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

router.get('/:communityId/calendar/events/:eventId/rsvp-counts', async (req, res, next) => {
  try {
    const { communityId, eventId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/${communityId}/events/${eventId}/rsvp-counts`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
});

// ---------------------------------------------------------------------------
// Ticketing (delegate to ticketController)
// ---------------------------------------------------------------------------

router.get('/:communityId/calendar/events/:eventId/ticket-types', requireCommunityAdmin, ticketController.listTicketTypes);
router.post('/:communityId/calendar/events/:eventId/ticket-types', requireCommunityAdmin, ticketController.createTicketType);
router.put('/:communityId/calendar/events/:eventId/ticket-types/:typeId', requireCommunityAdmin, ticketController.updateTicketType);
router.delete('/:communityId/calendar/events/:eventId/ticket-types/:typeId', requireCommunityAdmin, ticketController.deleteTicketType);

router.get('/:communityId/calendar/events/:eventId/tickets', requireCommunityAdmin, ticketController.listTickets);
router.post('/:communityId/calendar/events/:eventId/tickets', requireCommunityAdmin, ticketController.createTicket);
router.get('/:communityId/calendar/events/:eventId/tickets/:ticketId', requireCommunityAdmin, ticketController.getTicket);
router.post('/:communityId/calendar/events/:eventId/tickets/:ticketId/cancel', requireCommunityAdmin, ticketController.cancelTicket);
router.post('/:communityId/calendar/events/:eventId/tickets/:ticketId/transfer', requireCommunityAdmin, ticketController.transferTicket);

// ---------------------------------------------------------------------------
// Check-in
// ---------------------------------------------------------------------------

router.post('/calendar/verify-ticket', ticketController.verifyTicket);
router.post('/:communityId/calendar/events/:eventId/check-in', requireCommunityAdmin, ticketController.checkIn);
router.post('/:communityId/calendar/events/:eventId/tickets/:ticketId/undo-check-in', requireCommunityAdmin, ticketController.undoCheckIn);

// ---------------------------------------------------------------------------
// Attendance
// ---------------------------------------------------------------------------

router.get('/:communityId/calendar/events/:eventId/attendance', requireCommunityAdmin, ticketController.getAttendanceStats);
router.get('/:communityId/calendar/events/:eventId/check-in-log', requireCommunityAdmin, ticketController.getCheckInLog);
router.get('/:communityId/calendar/events/:eventId/attendance/export', requireCommunityAdmin, ticketController.exportAttendance);

// ---------------------------------------------------------------------------
// Event Admins
// ---------------------------------------------------------------------------

router.get('/:communityId/calendar/events/:eventId/admins', requireCommunityAdmin, ticketController.listEventAdmins);
router.post('/:communityId/calendar/events/:eventId/admins', requireCommunityAdmin, ticketController.assignEventAdmin);
router.put('/:communityId/calendar/events/:eventId/admins/:adminId', requireCommunityAdmin, ticketController.updateEventAdmin);
router.delete('/:communityId/calendar/events/:eventId/admins/:adminId', requireCommunityAdmin, ticketController.revokeEventAdmin);
router.get('/:communityId/calendar/events/:eventId/my-permissions', ticketController.getMyPermissions);

// ---------------------------------------------------------------------------
// Ticketing Config
// ---------------------------------------------------------------------------

router.post('/:communityId/calendar/events/:eventId/ticketing/enable', requireCommunityAdmin, ticketController.enableTicketing);
router.post('/:communityId/calendar/events/:eventId/ticketing/disable', requireCommunityAdmin, ticketController.disableTicketing);

export default router;
