"""
Tournament Bracket Service
===========================

Manages tournament brackets with support for single elimination,
double elimination, round robin, and swiss formats.

Bracket generation, match advancement, and standings are all handled here.
"""

import logging
import math
import random
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TournamentService:
    """
    Tournament bracket management with multiple format support.

    Bracket types:
    - single_elim: Standard elimination, BYEs for non-power-of-2
    - double_elim: Winners bracket + losers bracket
    - round_robin: All participants play each other
    - swiss: Paired by record, generated incrementally per round
    """

    def __init__(self, dal, config):
        self.dal = dal
        self.config = config

    # =========================================================================
    # Tournament CRUD
    # =========================================================================

    async def create_tournament(
        self,
        community_id: int,
        name: str,
        bracket_type: str = 'single_elim',
        max_participants: int = 64,
        description: str = None,
        event_id: int = None,
        prize_pool_points: int = 0,
        prize_giveaway_id: int = None,
        seeding_method: str = 'random',
        check_in_required: bool = False,
        registration_closes_at: datetime = None,
    ) -> Optional[dict]:
        """Create a new tournament."""
        max_allowed = getattr(self.config, 'TOURNAMENT_MAX_PARTICIPANTS', 256)
        if max_participants > max_allowed:
            return {'error': f'Max participants cannot exceed {max_allowed}'}

        valid_types = ('single_elim', 'double_elim', 'round_robin', 'swiss')
        if bracket_type not in valid_types:
            return {'error': f'Invalid bracket type. Must be one of: {valid_types}'}

        try:
            rows = await self.dal.execute(
                """
                INSERT INTO calendar_tournaments
                    (community_id, name, description, bracket_type,
                     max_participants, event_id, prize_pool_points,
                     prize_giveaway_id, seeding_method, check_in_required,
                     registration_closes_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id, name, bracket_type, status, max_participants
                """,
                [community_id, name, description, bracket_type,
                 max_participants, event_id, prize_pool_points,
                 prize_giveaway_id, seeding_method, check_in_required,
                 registration_closes_at],
            )
            return dict(rows[0]) if rows else None
        except Exception as e:
            logger.error("Error creating tournament: %s", e)
            return {'error': str(e)}

    async def get_tournament(self, tournament_id: int) -> Optional[dict]:
        """Get tournament details with participant count."""
        try:
            rows = await self.dal.execute(
                """
                SELECT t.*,
                       COUNT(p.id) as participant_count
                FROM calendar_tournaments t
                LEFT JOIN calendar_tournament_participants p
                    ON t.id = p.tournament_id
                WHERE t.id = $1
                GROUP BY t.id
                """,
                [tournament_id],
            )
            return dict(rows[0]) if rows else None
        except Exception as e:
            logger.error("Error getting tournament: %s", e)
            return None

    async def list_community_tournaments(
        self,
        community_id: int,
        status: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """List tournaments for a community."""
        try:
            if status:
                rows = await self.dal.execute(
                    """
                    SELECT t.*, COUNT(p.id) as participant_count
                    FROM calendar_tournaments t
                    LEFT JOIN calendar_tournament_participants p
                        ON t.id = p.tournament_id
                    WHERE t.community_id = $1 AND t.status = $2
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT $3
                    """,
                    [community_id, status, limit],
                )
            else:
                rows = await self.dal.execute(
                    """
                    SELECT t.*, COUNT(p.id) as participant_count
                    FROM calendar_tournaments t
                    LEFT JOIN calendar_tournament_participants p
                        ON t.id = p.tournament_id
                    WHERE t.community_id = $1
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT $2
                    """,
                    [community_id, limit],
                )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            logger.error("Error listing tournaments: %s", e)
            return []

    # =========================================================================
    # Registration
    # =========================================================================

    async def register_participant(
        self,
        tournament_id: int,
        user_id: str,
        platform: str,
        display_name: str = None,
    ) -> dict:
        """Register a participant for a tournament."""
        try:
            tournament = await self.get_tournament(tournament_id)
            if not tournament:
                return {'success': False, 'message': 'Tournament not found'}

            if tournament['status'] != 'registration':
                return {'success': False, 'message': 'Registration is closed'}

            if tournament['participant_count'] >= tournament['max_participants']:
                return {'success': False, 'message': 'Tournament is full'}

            await self.dal.execute(
                """
                INSERT INTO calendar_tournament_participants
                    (tournament_id, user_id, platform, display_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tournament_id, user_id) DO NOTHING
                """,
                [tournament_id, user_id, platform, display_name],
            )

            return {'success': True, 'message': 'Registered successfully'}
        except Exception as e:
            logger.error("Error registering participant: %s", e)
            return {'success': False, 'message': 'Registration failed'}

    # =========================================================================
    # Bracket Generation
    # =========================================================================

    async def seed_bracket(self, tournament_id: int) -> dict:
        """Seed participants and generate initial matches."""
        try:
            tournament = await self.get_tournament(tournament_id)
            if not tournament:
                return {'error': 'Tournament not found'}

            if tournament['status'] not in ('registration', 'seeding'):
                return {'error': 'Tournament cannot be seeded in current state'}

            # Get participants
            participants = await self.dal.execute(
                """
                SELECT * FROM calendar_tournament_participants
                WHERE tournament_id = $1
                ORDER BY id
                """,
                [tournament_id],
            )

            if not participants or len(participants) < 2:
                return {'error': 'Need at least 2 participants'}

            participants = list(participants)

            # Assign seeds
            if tournament['seeding_method'] == 'random':
                random.shuffle(participants)

            for i, p in enumerate(participants):
                await self.dal.execute(
                    "UPDATE calendar_tournament_participants SET seed = $1 WHERE id = $2",
                    [i + 1, p['id']],
                )

            # Generate matches based on bracket type
            bracket_type = tournament['bracket_type']
            if bracket_type == 'single_elim':
                total_rounds = await self._generate_single_elim(
                    tournament_id, participants,
                )
            elif bracket_type == 'double_elim':
                total_rounds = await self._generate_double_elim(
                    tournament_id, participants,
                )
            elif bracket_type == 'round_robin':
                total_rounds = await self._generate_round_robin(
                    tournament_id, participants,
                )
            elif bracket_type == 'swiss':
                total_rounds = await self._generate_swiss_round(
                    tournament_id, participants, round_number=1,
                )
            else:
                return {'error': f'Unknown bracket type: {bracket_type}'}

            # Update tournament status
            await self.dal.execute(
                """
                UPDATE calendar_tournaments
                SET status = 'seeding', total_rounds = $1, current_round = 1
                WHERE id = $2
                """,
                [total_rounds, tournament_id],
            )

            return {
                'success': True,
                'total_rounds': total_rounds,
                'participant_count': len(participants),
            }

        except Exception as e:
            logger.error("Error seeding bracket: %s", e)
            return {'error': str(e)}

    async def start_tournament(self, tournament_id: int) -> dict:
        """Transition tournament to active state."""
        try:
            await self.dal.execute(
                """
                UPDATE calendar_tournaments
                SET status = 'active', started_at = NOW()
                WHERE id = $1 AND status = 'seeding'
                """,
                [tournament_id],
            )

            # Mark first-round matches as ready
            await self.dal.execute(
                """
                UPDATE calendar_tournament_matches
                SET status = 'ready'
                WHERE tournament_id = $1 AND round_number = 1
                  AND participant_a_id IS NOT NULL
                  AND participant_b_id IS NOT NULL
                  AND status = 'pending'
                """,
                [tournament_id],
            )

            return {'success': True, 'message': 'Tournament started'}
        except Exception as e:
            logger.error("Error starting tournament: %s", e)
            return {'error': str(e)}

    # =========================================================================
    # Match Reporting & Advancement
    # =========================================================================

    async def report_match_result(
        self,
        tournament_id: int,
        match_id: int,
        winner_id: int,
        score_a: int = 0,
        score_b: int = 0,
    ) -> dict:
        """Report a match result and advance the bracket."""
        try:
            # Get match
            match_rows = await self.dal.execute(
                "SELECT * FROM calendar_tournament_matches WHERE id = $1 AND tournament_id = $2",
                [match_id, tournament_id],
            )
            if not match_rows:
                return {'error': 'Match not found'}

            match = match_rows[0]
            if match['status'] in ('completed', 'bye'):
                return {'error': 'Match already completed'}

            # Validate winner is a participant in this match
            if winner_id not in (match['participant_a_id'], match['participant_b_id']):
                return {'error': 'Winner must be a match participant'}

            loser_id = (
                match['participant_b_id']
                if winner_id == match['participant_a_id']
                else match['participant_a_id']
            )

            # Update match
            await self.dal.execute(
                """
                UPDATE calendar_tournament_matches
                SET winner_id = $1, score_a = $2, score_b = $3,
                    status = 'completed', completed_at = NOW()
                WHERE id = $4
                """,
                [winner_id, score_a, score_b, match_id],
            )

            # Update participant records
            await self.dal.execute(
                "UPDATE calendar_tournament_participants SET wins = wins + 1 WHERE id = $1",
                [winner_id],
            )
            if loser_id:
                await self.dal.execute(
                    "UPDATE calendar_tournament_participants SET losses = losses + 1 WHERE id = $1",
                    [loser_id],
                )

            # Advance bracket
            tournament = await self.get_tournament(tournament_id)
            await self._advance_bracket(tournament, match, winner_id, loser_id)

            return {'success': True, 'winner_id': winner_id}

        except Exception as e:
            logger.error("Error reporting match result: %s", e)
            return {'error': str(e)}

    async def get_bracket_state(self, tournament_id: int) -> dict:
        """Get full bracket view with all rounds and matches."""
        try:
            tournament = await self.get_tournament(tournament_id)
            if not tournament:
                return {'error': 'Tournament not found'}

            matches = await self.dal.execute(
                """
                SELECT m.*,
                       pa.display_name as participant_a_name,
                       pa.seed as participant_a_seed,
                       pb.display_name as participant_b_name,
                       pb.seed as participant_b_seed,
                       pw.display_name as winner_name
                FROM calendar_tournament_matches m
                LEFT JOIN calendar_tournament_participants pa ON m.participant_a_id = pa.id
                LEFT JOIN calendar_tournament_participants pb ON m.participant_b_id = pb.id
                LEFT JOIN calendar_tournament_participants pw ON m.winner_id = pw.id
                WHERE m.tournament_id = $1
                ORDER BY m.bracket_position, m.round_number, m.match_number
                """,
                [tournament_id],
            )

            # Group by round
            rounds = {}
            for m in (matches or []):
                m = dict(m)
                rn = m['round_number']
                if rn not in rounds:
                    rounds[rn] = []
                rounds[rn].append(m)

            return {
                'tournament': tournament,
                'rounds': rounds,
                'total_matches': len(matches or []),
            }

        except Exception as e:
            logger.error("Error getting bracket state: %s", e)
            return {'error': str(e)}

    async def get_standings(self, tournament_id: int) -> list[dict]:
        """Get tournament standings sorted by wins then losses."""
        try:
            rows = await self.dal.execute(
                """
                SELECT id, user_id, platform, display_name, seed,
                       wins, losses, draws, is_eliminated
                FROM calendar_tournament_participants
                WHERE tournament_id = $1
                ORDER BY wins DESC, losses ASC, seed ASC
                """,
                [tournament_id],
            )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            logger.error("Error getting standings: %s", e)
            return []

    async def complete_tournament(self, tournament_id: int) -> dict:
        """Complete tournament and award prizes if configured."""
        try:
            tournament = await self.get_tournament(tournament_id)
            if not tournament:
                return {'error': 'Tournament not found'}

            await self.dal.execute(
                """
                UPDATE calendar_tournaments
                SET status = 'completed', completed_at = NOW()
                WHERE id = $1
                """,
                [tournament_id],
            )

            return {
                'success': True,
                'message': 'Tournament completed',
                'prize_pool_points': tournament.get('prize_pool_points', 0),
            }

        except Exception as e:
            logger.error("Error completing tournament: %s", e)
            return {'error': str(e)}

    # =========================================================================
    # Bracket Generation Helpers
    # =========================================================================

    async def _generate_single_elim(
        self,
        tournament_id: int,
        participants: list,
    ) -> int:
        """Generate single elimination bracket with BYEs for non-power-of-2."""
        n = len(participants)
        bracket_size = 2 ** math.ceil(math.log2(n))
        total_rounds = int(math.log2(bracket_size))
        num_byes = bracket_size - n

        # Pad with None for BYEs (top seeds get byes)
        seeded = list(participants) + [None] * num_byes

        # Generate round 1 matches
        match_num = 0
        for i in range(0, bracket_size, 2):
            match_num += 1
            a = seeded[i]
            b = seeded[i + 1]

            a_id = a['id'] if a else None
            b_id = b['id'] if b else None

            # Determine if this is a BYE match
            is_bye = a_id is None or b_id is None
            status = 'bye' if is_bye else 'pending'
            winner = a_id if b_id is None else (b_id if a_id is None else None)

            await self.dal.execute(
                """
                INSERT INTO calendar_tournament_matches
                    (tournament_id, round_number, match_number,
                     bracket_position, participant_a_id, participant_b_id,
                     winner_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                [tournament_id, 1, match_num, 'WB',
                 a_id, b_id, winner, status],
            )

        # Generate placeholder matches for subsequent rounds
        for rnd in range(2, total_rounds + 1):
            matches_in_round = bracket_size // (2 ** rnd)
            for m in range(1, matches_in_round + 1):
                await self.dal.execute(
                    """
                    INSERT INTO calendar_tournament_matches
                        (tournament_id, round_number, match_number,
                         bracket_position, status)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [tournament_id, rnd, m, 'WB', 'pending'],
                )

        return total_rounds

    async def _generate_double_elim(
        self,
        tournament_id: int,
        participants: list,
    ) -> int:
        """Generate double elimination bracket (winners + losers bracket)."""
        n = len(participants)
        bracket_size = 2 ** math.ceil(math.log2(n))
        wb_rounds = int(math.log2(bracket_size))

        # Winners bracket round 1
        seeded = list(participants) + [None] * (bracket_size - n)
        match_num = 0
        for i in range(0, bracket_size, 2):
            match_num += 1
            a = seeded[i]
            b = seeded[i + 1]
            a_id = a['id'] if a else None
            b_id = b['id'] if b else None
            is_bye = a_id is None or b_id is None
            status = 'bye' if is_bye else 'pending'
            winner = a_id if b_id is None else (b_id if a_id is None else None)

            await self.dal.execute(
                """
                INSERT INTO calendar_tournament_matches
                    (tournament_id, round_number, match_number,
                     bracket_position, participant_a_id, participant_b_id,
                     winner_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                [tournament_id, 1, match_num, 'WB',
                 a_id, b_id, winner, status],
            )

        # Placeholder WB rounds
        for rnd in range(2, wb_rounds + 1):
            matches_in_round = bracket_size // (2 ** rnd)
            for m in range(1, matches_in_round + 1):
                await self.dal.execute(
                    """
                    INSERT INTO calendar_tournament_matches
                        (tournament_id, round_number, match_number,
                         bracket_position, status)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [tournament_id, rnd, m, 'WB', 'pending'],
                )

        # Losers bracket: roughly 2 * (wb_rounds - 1) rounds
        lb_rounds = 2 * (wb_rounds - 1)
        for rnd in range(1, lb_rounds + 1):
            # LB match count decreases over rounds
            if rnd % 2 == 1:
                matches_in_round = bracket_size // (2 ** ((rnd + 1) // 2 + 1))
            else:
                matches_in_round = bracket_size // (2 ** (rnd // 2 + 1))
            matches_in_round = max(1, matches_in_round)

            for m in range(1, matches_in_round + 1):
                await self.dal.execute(
                    """
                    INSERT INTO calendar_tournament_matches
                        (tournament_id, round_number, match_number,
                         bracket_position, status)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [tournament_id, rnd, m, 'LB', 'pending'],
                )

        # Grand finals (1-2 matches)
        total_rounds = wb_rounds + lb_rounds + 1
        await self.dal.execute(
            """
            INSERT INTO calendar_tournament_matches
                (tournament_id, round_number, match_number,
                 bracket_position, status)
            VALUES ($1, $2, $3, $4, $5)
            """,
            [tournament_id, total_rounds, 1, 'WB', 'pending'],
        )

        return total_rounds

    async def _generate_round_robin(
        self,
        tournament_id: int,
        participants: list,
    ) -> int:
        """Generate round robin — all pairs play each other."""
        n = len(participants)
        # Round robin needs n-1 rounds (or n if odd, with byes)
        total_rounds = n - 1 if n % 2 == 0 else n

        match_num = 0
        rnd = 1
        # Generate all pairings using circle method
        items = list(range(n))
        if n % 2 == 1:
            items.append(None)  # BYE placeholder

        half = len(items) // 2
        for _ in range(len(items) - 1):
            for i in range(half):
                a_idx = items[i]
                b_idx = items[-(i + 1)]

                if a_idx is None or b_idx is None:
                    continue  # Skip BYE rounds

                match_num += 1
                await self.dal.execute(
                    """
                    INSERT INTO calendar_tournament_matches
                        (tournament_id, round_number, match_number,
                         bracket_position, participant_a_id, participant_b_id,
                         status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    [tournament_id, rnd, match_num, 'WB',
                     participants[a_idx]['id'], participants[b_idx]['id'],
                     'pending'],
                )

            # Rotate (keep first element fixed)
            items.insert(1, items.pop())
            rnd += 1
            match_num = 0

        return total_rounds

    async def _generate_swiss_round(
        self,
        tournament_id: int,
        participants: list,
        round_number: int = 1,
    ) -> int:
        """Generate one round of swiss pairings based on current records."""
        if round_number == 1:
            # First round: random pairing
            shuffled = list(participants)
            random.shuffle(shuffled)
        else:
            # Pair by record (most wins play most wins)
            standings = await self.get_standings(tournament_id)
            shuffled = standings

        match_num = 0
        for i in range(0, len(shuffled) - 1, 2):
            match_num += 1
            a = shuffled[i]
            b = shuffled[i + 1]

            await self.dal.execute(
                """
                INSERT INTO calendar_tournament_matches
                    (tournament_id, round_number, match_number,
                     bracket_position, participant_a_id, participant_b_id,
                     status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                [tournament_id, round_number, match_num, 'WB',
                 a['id'], b['id'], 'pending'],
            )

        # Swiss typically runs ceil(log2(n)) rounds
        n = len(participants)
        total_rounds = math.ceil(math.log2(n))
        return total_rounds

    # =========================================================================
    # Bracket Advancement
    # =========================================================================

    async def _advance_bracket(
        self,
        tournament: dict,
        match: dict,
        winner_id: int,
        loser_id: int,
    ) -> None:
        """Advance winner to next round match in the bracket."""
        bracket_type = tournament['bracket_type']

        if bracket_type == 'single_elim':
            await self._advance_single_elim(
                tournament['id'], match, winner_id,
            )
        elif bracket_type == 'double_elim':
            await self._advance_double_elim(
                tournament['id'], match, winner_id, loser_id,
            )
            # Mark loser as eliminated only if they lose in LB
            if match['bracket_position'] == 'LB' and loser_id:
                await self.dal.execute(
                    """
                    UPDATE calendar_tournament_participants
                    SET is_eliminated = TRUE WHERE id = $1
                    """,
                    [loser_id],
                )
        elif bracket_type == 'swiss':
            # Check if all matches in current round are done
            pending = await self.dal.execute(
                """
                SELECT COUNT(*) as cnt FROM calendar_tournament_matches
                WHERE tournament_id = $1 AND round_number = $2
                  AND status NOT IN ('completed', 'bye')
                """,
                [tournament['id'], match['round_number']],
            )
            if pending and pending[0]['cnt'] == 0:
                # Generate next swiss round
                current = match['round_number']
                if current < tournament['total_rounds']:
                    participants = await self.dal.execute(
                        """
                        SELECT * FROM calendar_tournament_participants
                        WHERE tournament_id = $1
                        ORDER BY wins DESC, losses ASC
                        """,
                        [tournament['id']],
                    )
                    if participants:
                        await self._generate_swiss_round(
                            tournament['id'],
                            list(participants),
                            round_number=current + 1,
                        )
                        await self.dal.execute(
                            "UPDATE calendar_tournaments SET current_round = $1 WHERE id = $2",
                            [current + 1, tournament['id']],
                        )

        # For single_elim and round_robin, mark loser as eliminated
        if bracket_type == 'single_elim' and loser_id:
            await self.dal.execute(
                """
                UPDATE calendar_tournament_participants
                SET is_eliminated = TRUE WHERE id = $1
                """,
                [loser_id],
            )

    async def _advance_single_elim(
        self,
        tournament_id: int,
        match: dict,
        winner_id: int,
    ) -> None:
        """Place winner into the next round's match slot."""
        next_round = match['round_number'] + 1
        next_match_num = (match['match_number'] + 1) // 2

        # Find the next match
        next_matches = await self.dal.execute(
            """
            SELECT * FROM calendar_tournament_matches
            WHERE tournament_id = $1 AND round_number = $2
              AND match_number = $3 AND bracket_position = 'WB'
            """,
            [tournament_id, next_round, next_match_num],
        )

        if not next_matches:
            return  # Finals — no next match

        next_match = next_matches[0]

        # Place winner in the appropriate slot
        if match['match_number'] % 2 == 1:
            await self.dal.execute(
                "UPDATE calendar_tournament_matches SET participant_a_id = $1 WHERE id = $2",
                [winner_id, next_match['id']],
            )
        else:
            await self.dal.execute(
                "UPDATE calendar_tournament_matches SET participant_b_id = $1 WHERE id = $2",
                [winner_id, next_match['id']],
            )

        # If both slots are filled, mark as ready
        updated = await self.dal.execute(
            """
            SELECT participant_a_id, participant_b_id
            FROM calendar_tournament_matches WHERE id = $1
            """,
            [next_match['id']],
        )
        if updated and updated[0]['participant_a_id'] and updated[0]['participant_b_id']:
            await self.dal.execute(
                "UPDATE calendar_tournament_matches SET status = 'ready' WHERE id = $1",
                [next_match['id']],
            )

    async def _advance_double_elim(
        self,
        tournament_id: int,
        match: dict,
        winner_id: int,
        loser_id: int,
    ) -> None:
        """
        Advance in double elimination.
        WB losers drop to LB. LB losers are eliminated.
        """
        if match['bracket_position'] == 'WB':
            # Winner advances in WB
            await self._advance_single_elim(tournament_id, match, winner_id)
            # Loser drops to losers bracket (find next available LB slot)
            if loser_id:
                lb_matches = await self.dal.execute(
                    """
                    SELECT * FROM calendar_tournament_matches
                    WHERE tournament_id = $1 AND bracket_position = 'LB'
                      AND status = 'pending'
                      AND (participant_a_id IS NULL OR participant_b_id IS NULL)
                    ORDER BY round_number, match_number
                    LIMIT 1
                    """,
                    [tournament_id],
                )
                if lb_matches:
                    lb_match = lb_matches[0]
                    slot = 'participant_a_id' if lb_match['participant_a_id'] is None else 'participant_b_id'
                    await self.dal.execute(
                        f"UPDATE calendar_tournament_matches SET {slot} = $1 WHERE id = $2",
                        [loser_id, lb_match['id']],
                    )
        else:
            # LB winner advances in LB
            next_lb = await self.dal.execute(
                """
                SELECT * FROM calendar_tournament_matches
                WHERE tournament_id = $1 AND bracket_position = 'LB'
                  AND round_number > $2 AND status = 'pending'
                  AND (participant_a_id IS NULL OR participant_b_id IS NULL)
                ORDER BY round_number, match_number
                LIMIT 1
                """,
                [tournament_id, match['round_number']],
            )
            if next_lb:
                slot = 'participant_a_id' if next_lb[0]['participant_a_id'] is None else 'participant_b_id'
                await self.dal.execute(
                    f"UPDATE calendar_tournament_matches SET {slot} = $1 WHERE id = $2",
                    [winner_id, next_lb[0]['id']],
                )
