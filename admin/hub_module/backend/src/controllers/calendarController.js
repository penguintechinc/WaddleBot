/**
 * Calendar Controller
 * User-facing calendar operations: OAuth, availability, booking pages,
 * public booking, user bookings, and group scheduling.
 * All requests proxy to the calendar-interaction service.
 */
import { proxyToCalendar, buildUserContext } from '../utils/calendarProxy.js';

// ---------------------------------------------------------------------------
// OAuth
// ---------------------------------------------------------------------------

export async function getGoogleAuthUrl(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/oauth/google/auth-url', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getMicrosoftAuthUrl(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/oauth/microsoft/auth-url', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getConnectedCalendars(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/oauth/calendars', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function syncCalendar(req, res, next) {
  try {
    const { id } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/oauth/calendars/${id}/sync`, {
      method: 'POST',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function disconnectCalendar(req, res, next) {
  try {
    const { id } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/oauth/calendars/${id}`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

// ---------------------------------------------------------------------------
// Availability
// ---------------------------------------------------------------------------

export async function getAvailabilitySettings(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/availability/settings', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function updateAvailabilitySettings(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/availability/settings', {
      method: 'PUT',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getWeeklyAvailability(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/availability/weekly', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function updateWeeklyAvailability(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/availability/weekly', {
      method: 'PUT',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getAvailableSlots(req, res, next) {
  try {
    const { userId } = req.params;
    const queryParams = new URLSearchParams();
    if (req.query.start) queryParams.set('start', req.query.start);
    if (req.query.end) queryParams.set('end', req.query.end);
    if (req.query.duration) queryParams.set('duration', req.query.duration);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/availability/${userId}/slots${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

// ---------------------------------------------------------------------------
// Booking Pages
// ---------------------------------------------------------------------------

export async function createBookingPage(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/booking-pages', {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.status(201).json(data);
  } catch (err) { next(err); }
}

export async function getBookingPages(req, res, next) {
  try {
    const data = await proxyToCalendar('/api/v1/calendar/booking-pages', {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getBookingPage(req, res, next) {
  try {
    const { id } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${id}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function updateBookingPage(req, res, next) {
  try {
    const { id } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${id}`, {
      method: 'PUT',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function deleteBookingPage(req, res, next) {
  try {
    const { id } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${id}`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

// ---------------------------------------------------------------------------
// Public Booking
// ---------------------------------------------------------------------------

export async function getBookingSlots(req, res, next) {
  try {
    const { slug } = req.params;
    const queryParams = new URLSearchParams();
    if (req.query.start) queryParams.set('start', req.query.start);
    if (req.query.end) queryParams.set('end', req.query.end);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/book/${slug}/slots${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function createBooking(req, res, next) {
  try {
    const { slug } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/book/${slug}`, {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.status(201).json(data);
  } catch (err) { next(err); }
}

// ---------------------------------------------------------------------------
// User Bookings
// ---------------------------------------------------------------------------

export async function getMyBookings(req, res, next) {
  try {
    const queryParams = new URLSearchParams();
    if (req.query.status) queryParams.set('status', req.query.status);
    if (req.query.limit) queryParams.set('limit', req.query.limit);
    if (req.query.offset) queryParams.set('offset', req.query.offset);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/my-bookings${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getBooking(req, res, next) {
  try {
    const { uuid } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/bookings/${uuid}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function cancelBooking(req, res, next) {
  try {
    const { uuid } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/bookings/${uuid}`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

// ---------------------------------------------------------------------------
// Group Scheduling
// ---------------------------------------------------------------------------

export async function addGroupMember(req, res, next) {
  try {
    const { pageId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${pageId}/members`, {
      method: 'POST',
      body: JSON.stringify(req.body),
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.status(201).json(data);
  } catch (err) { next(err); }
}

export async function removeGroupMember(req, res, next) {
  try {
    const { pageId, userId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${pageId}/members/${userId}`, {
      method: 'DELETE',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getGroupMembers(req, res, next) {
  try {
    const { pageId } = req.params;
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${pageId}/members`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getGroupAvailability(req, res, next) {
  try {
    const { pageId } = req.params;
    const queryParams = new URLSearchParams();
    if (req.query.start) queryParams.set('start', req.query.start);
    if (req.query.end) queryParams.set('end', req.query.end);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${pageId}/group-availability${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}

export async function getBestSlots(req, res, next) {
  try {
    const { pageId } = req.params;
    const queryParams = new URLSearchParams();
    if (req.query.start) queryParams.set('start', req.query.start);
    if (req.query.end) queryParams.set('end', req.query.end);
    if (req.query.duration) queryParams.set('duration', req.query.duration);
    const qs = queryParams.toString();
    const data = await proxyToCalendar(`/api/v1/calendar/booking-pages/${pageId}/best-slots${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      headers: { 'X-User-Context': buildUserContext(req) },
    });
    res.json(data);
  } catch (err) { next(err); }
}
