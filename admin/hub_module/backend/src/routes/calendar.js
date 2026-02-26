/**
 * Calendar Routes (User-facing)
 * OAuth, availability, booking pages, public booking, user bookings, group scheduling.
 */
import { Router } from 'express';
import * as calendarController from '../controllers/calendarController.js';
import { requireAuth, optionalAuth } from '../middleware/auth.js';

const router = Router();

// OAuth
router.get('/oauth/google/auth-url', requireAuth, calendarController.getGoogleAuthUrl);
router.get('/oauth/microsoft/auth-url', requireAuth, calendarController.getMicrosoftAuthUrl);
router.get('/oauth/calendars', requireAuth, calendarController.getConnectedCalendars);
router.post('/oauth/calendars/:id/sync', requireAuth, calendarController.syncCalendar);
router.delete('/oauth/calendars/:id', requireAuth, calendarController.disconnectCalendar);

// Availability
router.get('/availability/settings', requireAuth, calendarController.getAvailabilitySettings);
router.put('/availability/settings', requireAuth, calendarController.updateAvailabilitySettings);
router.get('/availability/weekly', requireAuth, calendarController.getWeeklyAvailability);
router.put('/availability/weekly', requireAuth, calendarController.updateWeeklyAvailability);
router.get('/availability/:userId/slots', requireAuth, calendarController.getAvailableSlots);

// Booking pages
router.post('/booking-pages', requireAuth, calendarController.createBookingPage);
router.get('/booking-pages', requireAuth, calendarController.getBookingPages);
router.get('/booking-pages/:id', requireAuth, calendarController.getBookingPage);
router.put('/booking-pages/:id', requireAuth, calendarController.updateBookingPage);
router.delete('/booking-pages/:id', requireAuth, calendarController.deleteBookingPage);

// Public booking (optional auth)
router.get('/book/:slug/slots', optionalAuth, calendarController.getBookingSlots);
router.post('/book/:slug', optionalAuth, calendarController.createBooking);

// User bookings
router.get('/my-bookings', requireAuth, calendarController.getMyBookings);
router.get('/bookings/:uuid', requireAuth, calendarController.getBooking);
router.delete('/bookings/:uuid', requireAuth, calendarController.cancelBooking);

// Group scheduling
router.post('/booking-pages/:pageId/members', requireAuth, calendarController.addGroupMember);
router.delete('/booking-pages/:pageId/members/:userId', requireAuth, calendarController.removeGroupMember);
router.get('/booking-pages/:pageId/members', requireAuth, calendarController.getGroupMembers);
router.get('/booking-pages/:pageId/group-availability', requireAuth, calendarController.getGroupAvailability);
router.get('/booking-pages/:pageId/best-slots', requireAuth, calendarController.getBestSlots);

export default router;
