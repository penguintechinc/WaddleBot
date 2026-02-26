/**
 * Community Calls Controller
 * Proxies requests to the module_rtc service for WebRTC call management
 */
import axios from 'axios';
import logger from '../utils/logger.js';

const MODULE_RTC_URL = process.env.MODULE_RTC_URL || 'http://core-module-rtc:8093';

/**
 * Get all call rooms for a community
 */
export async function getCallRooms(req, res) {
  try {
    const { communityId } = req.params;
    const response = await axios.get(`${MODULE_RTC_URL}/api/v1/rooms`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, rooms: response.data.rooms || [] });
  } catch (error) {
    logger.error('Failed to get call rooms:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, rooms: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get call rooms'
    });
  }
}

/**
 * Get a specific call room
 */
export async function getCallRoom(req, res) {
  try {
    const { communityId, roomName } = req.params;
    const response = await axios.get(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, ...response.data });
  } catch (error) {
    logger.error('Failed to get call room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get call room'
    });
  }
}

/**
 * Create a new call room
 */
export async function createCallRoom(req, res) {
  try {
    const { communityId } = req.params;
    const { room_name, max_participants } = req.body;
    const response = await axios.post(`${MODULE_RTC_URL}/api/v1/rooms`, {
      community_id: communityId,
      room_name,
      max_participants: max_participants || 100
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.status(201).json({ success: true, ...response.data });
  } catch (error) {
    logger.error('Failed to create call room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to create call room'
    });
  }
}

/**
 * Delete a call room
 */
export async function deleteCallRoom(req, res) {
  try {
    const { communityId, roomName } = req.params;
    await axios.delete(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Room deleted' });
  } catch (error) {
    logger.error('Failed to delete call room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to delete call room'
    });
  }
}

/**
 * Lock a call room
 */
export async function lockCallRoom(req, res) {
  try {
    const { communityId, roomName } = req.params;
    await axios.post(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/lock`, {
      community_id: communityId
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Room locked' });
  } catch (error) {
    logger.error('Failed to lock call room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to lock room'
    });
  }
}

/**
 * Unlock a call room
 */
export async function unlockCallRoom(req, res) {
  try {
    const { communityId, roomName } = req.params;
    await axios.post(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/unlock`, {
      community_id: communityId
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Room unlocked' });
  } catch (error) {
    logger.error('Failed to unlock call room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to unlock room'
    });
  }
}

/**
 * Get participants in a room
 */
export async function getCallParticipants(req, res) {
  try {
    const { communityId, roomName } = req.params;
    const response = await axios.get(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/participants`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, participants: response.data.participants || [] });
  } catch (error) {
    logger.error('Failed to get participants:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, participants: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get participants'
    });
  }
}

/**
 * Kick a participant from a room
 */
export async function kickCallParticipant(req, res) {
  try {
    const { communityId, roomName } = req.params;
    const { identity } = req.body;
    await axios.post(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/kick`, {
      community_id: communityId,
      identity
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Participant removed' });
  } catch (error) {
    logger.error('Failed to kick participant:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to kick participant'
    });
  }
}

/**
 * Mute all participants in a room
 */
export async function muteAllCallParticipants(req, res) {
  try {
    const { communityId, roomName } = req.params;
    await axios.post(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/mute-all`, {
      community_id: communityId
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'All participants muted' });
  } catch (error) {
    logger.error('Failed to mute all:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to mute all'
    });
  }
}

/**
 * Get raised hands queue
 */
export async function getRaisedHands(req, res) {
  try {
    const { communityId, roomName } = req.params;
    const response = await axios.get(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/raised-hands`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, raised_hands: response.data.raised_hands || [] });
  } catch (error) {
    logger.error('Failed to get raised hands:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, raised_hands: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get raised hands'
    });
  }
}

/**
 * Join a voice room (member-facing) — gets a LiveKit token
 */
export async function joinVoiceRoom(req, res) {
  try {
    const communityId = req.params.communityId || req.params.id;
    const { roomName } = req.params;
    const response = await axios.post(
      `${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/join`,
      {
        community_id: communityId,
        user_id: String(req.user?.id),
        username: req.user?.username,
      },
      { headers: { Authorization: req.headers.authorization } }
    );
    res.json({ success: true, token: response.data.token, url: response.data.url });
  } catch (error) {
    logger.error('Failed to join voice room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to join room'
    });
  }
}

/**
 * Leave a voice room (member-facing)
 */
export async function leaveVoiceRoom(req, res) {
  try {
    const communityId = req.params.communityId || req.params.id;
    const { roomName } = req.params;
    await axios.post(
      `${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/leave`,
      {
        community_id: communityId,
        user_id: String(req.user?.id),
      },
      { headers: { Authorization: req.headers.authorization } }
    );
    res.json({ success: true, message: 'Left room' });
  } catch (error) {
    logger.error('Failed to leave voice room:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to leave room'
    });
  }
}

/**
 * Acknowledge a raised hand
 */
export async function acknowledgeHand(req, res) {
  try {
    const { communityId, roomName } = req.params;
    const { user_id } = req.body;
    await axios.post(`${MODULE_RTC_URL}/api/v1/rooms/${encodeURIComponent(roomName)}/acknowledge-hand`, {
      community_id: communityId,
      user_id
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Hand acknowledged' });
  } catch (error) {
    logger.error('Failed to acknowledge hand:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to acknowledge hand'
    });
  }
}
