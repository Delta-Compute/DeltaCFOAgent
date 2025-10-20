#!/usr/bin/env python3
"""
Revenue Matcher - Sistema Inteligente de Matching de Invoices com Transações
Automatiza a identificação de invoices pagos através de análise de transações

Funcionalidades:
- Matching por valor (exato e aproximado)
- Matching por data (vencimento vs data transação)
- Matching por vendor/descrição (fuzzy matching)
- Matching semântico com Claude AI
- Sistema de pontuação e confiança
- Aprendizado de padrões
"""

import os
import re
import json
import logging
import concurrent.futures
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import anthropic
from database import db_manager
# from learning_system import apply_learning_to_scores, record_match_feedback  # TODO: Implement learning system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """Resultado de matching entre invoice e transação"""
    invoice_id: str
    transaction_id: str
    score: float
    match_type: str
    criteria_scores: Dict[str, float]
    confidence_level: str
    explanation: str
    auto_match: bool

class RevenueInvoiceMatcher:
    """
    Motor principal de matching entre invoices e transações
    """

    def __init__(self):
        self.claude_client = self._init_claude_client()
        self.match_threshold_high = 0.80  # Match automático (reduzido de 0.90)
        self.match_threshold_medium = 0.55  # Match sugerido (reduzido de 0.70)
        self.amount_tolerance = 0.03  # 3% tolerance for amount matching (aumentado de 0.02)

        # Progress tracking
        self.progress_lock = threading.Lock()
        self.current_progress = 0
        self.total_progress = 0
        self.start_time = None
        self.ai_filter_threshold_low = 0.4   # Apenas IA para scores 0.4-0.8
        self.ai_filter_threshold_high = 0.8
        self.batch_size = 18  # Batch processing size
        self.max_workers = 3  # Parallel threads

    def _init_claude_client(self):
        """Inicializa cliente Claude para matching semântico"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                return anthropic.Anthropic(api_key=api_key.strip())
            else:
                logger.warning("Claude API key not found - semantic matching disabled")
                return None
        except Exception as e:
            logger.error(f"Error initializing Claude: {e}")
            return None

    def _sanitize_text(self, text: str) -> str:
        """Sanitiza texto para evitar erros JSON em Claude API"""
        if not text:
            return ""
        # Remove caracteres de controle que causam JSON errors
        sanitized = text.encode('ascii', 'ignore').decode('ascii')
        # Remove quebras de linha que podem corromper JSON
        sanitized = sanitized.replace('\n', ' ').replace('\r', ' ')
        # Remove aspas duplas que podem quebrar JSON
        sanitized = sanitized.replace('"', "'")
        return sanitized.strip()

    def update_progress(self, processed: int = None):
        """Atualiza progresso thread-safe"""
        with self.progress_lock:
            if processed is not None:
                self.current_progress = processed
            else:
                self.current_progress += 1

    def get_progress_info(self) -> Dict[str, Any]:
        """Retorna informações de progresso thread-safe"""
        with self.progress_lock:
            if self.total_progress == 0:
                return {"progress": 0, "eta": "N/A", "matches_processed": 0, "total": 0}

            progress_percent = (self.current_progress / self.total_progress) * 100

            if self.start_time and self.current_progress > 0:
                elapsed = time.time() - self.start_time
                rate = self.current_progress / elapsed
                remaining = (self.total_progress - self.current_progress) / rate if rate > 0 else 0
                eta = f"{int(remaining//60)}:{int(remaining%60):02d}"
            else:
                eta = "N/A"

            return {
                "progress": round(progress_percent, 1),
                "eta": eta,
                "matches_processed": self.current_progress,
                "total": self.total_progress
            }

    def find_matches_for_invoices(self, invoice_ids: List[str] = None) -> List[MatchResult]:
        """
        Encontra matches para invoices específicos ou todos os não matchados

        Args:
            invoice_ids: Lista de IDs de invoices. Se None, processa todos não matchados

        Returns:
            Lista de MatchResult com os matches encontrados
        """
        logger.info(f"Starting invoice matching process...")

        # Buscar invoices não matchados
        invoices = self._get_unmatched_invoices(invoice_ids)
        if not invoices:
            logger.info("No unmatched invoices found")
            return []

        # Buscar transações candidatas (últimos 6 meses)
        transactions = self._get_candidate_transactions()
        if not transactions:
            logger.info("No candidate transactions found")
            return []

        logger.info(f"Processing {len(invoices)} invoices against {len(transactions)} transactions")

        matches = []
        for invoice in invoices:
            invoice_matches = self._find_matches_for_single_invoice(invoice, transactions)
            matches.extend(invoice_matches)

        # Ordenar por score descendente
        matches.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(matches)} potential matches")
        return matches

    def _get_unmatched_invoices(self, invoice_ids: List[str] = None) -> List[Dict]:
        """Busca invoices que ainda não foram matchados"""
        query = """
            SELECT id, invoice_number, date, due_date, vendor_name,
                   total_amount, currency, business_unit, linked_transaction_id
            FROM invoices
            WHERE (linked_transaction_id IS NULL OR linked_transaction_id = '')
        """
        params = []

        if invoice_ids:
            placeholders = ', '.join(['?' if db_manager.db_type == 'sqlite' else '%s'] * len(invoice_ids))
            query += f" AND id IN ({placeholders})"
            params.extend(invoice_ids)

        query += " ORDER BY date DESC"

        try:
            return db_manager.execute_query(query, tuple(params), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching unmatched invoices: {e}")
            return []

    def _get_candidate_transactions(self, days_back: int = None) -> List[Dict]:
        """
        🚀 OTIMIZADO: Busca transações candidatas com filtro de data INTELIGENTE
        Prioriza transações recentes mas permite histórico razoável para matches
        """
        # Use parâmetro ou default inteligente: 2 anos para dados históricos
        if days_back is None:
            days_back = 730  # 2 anos máximo - invoices não são pagos após anos

        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        query = """
            SELECT transaction_id, date, description, amount, currency,
                   classified_entity, origin, destination, source_file
            FROM transactions
            WHERE ABS(amount) > 0.01
              AND date >= ?
            ORDER BY date DESC
        """

        # Adjust for PostgreSQL
        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            transactions = db_manager.execute_query(query, (cutoff_date,), fetch_all=True)
            logger.info(f"🚀 SMART FILTERING: Found {len(transactions)} transactions from last {days_back} days ({cutoff_date}+)")

            # Clean and validate transactions
            valid_transactions = []
            for t in transactions:
                try:
                    # Validate amount field - convert Decimal to float safely
                    if hasattr(t['amount'], 'to_eng_string'):  # PostgreSQL Decimal
                        t['amount'] = float(t['amount'])
                    elif isinstance(t['amount'], str):
                        t['amount'] = float(t['amount'])

                    # Skip transactions with invalid amounts
                    if abs(t['amount']) > 0.01:  # Only meaningful amounts
                        valid_transactions.append(t)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Skipping transaction {t.get('transaction_id', 'unknown')} with invalid amount: {e}")
                    continue

            # Log breakdown
            positive = len([t for t in valid_transactions if t['amount'] > 0])
            negative = len([t for t in valid_transactions if t['amount'] < 0])
            logger.info(f"   📊 Valid transactions: {len(valid_transactions)} ({positive} positive, {negative} negative)")

            return valid_transactions
        except Exception as e:
            logger.error(f"Error fetching candidate transactions: {e}")
            return []

    def _find_matches_for_single_invoice(self, invoice: Dict, transactions: List[Dict]) -> List[MatchResult]:
        """Encontra matches para um único invoice"""
        matches = []

        for transaction in transactions:
            match_result = self._evaluate_match(invoice, transaction)
            if match_result and match_result.score >= self.match_threshold_medium:
                matches.append(match_result)

        return matches

    def _evaluate_match(self, invoice: Dict, transaction: Dict) -> Optional[MatchResult]:
        """Avalia se um invoice e transação são um match"""

        # Verificar critérios básicos
        criteria_scores = {}

        # 1. Matching por valor
        amount_score = self._calculate_amount_match_score(invoice, transaction)
        criteria_scores['amount'] = amount_score

        # 2. Matching por data
        date_score = self._calculate_date_match_score(invoice, transaction)
        criteria_scores['date'] = date_score

        # 3. Matching por vendor/descrição
        vendor_score = self._calculate_vendor_match_score(invoice, transaction)
        criteria_scores['vendor'] = vendor_score

        # 4. Matching por business unit/entity
        entity_score = self._calculate_entity_match_score(invoice, transaction)
        criteria_scores['entity'] = entity_score

        # 5. Pattern matching (invoice number, etc.)
        pattern_score = self._calculate_pattern_match_score(invoice, transaction)
        criteria_scores['pattern'] = pattern_score

        # Calcular score final ponderado com lógica adaptativa
        # Se vendor score é baixo mas entity score é alto, reduzir peso do vendor
        if vendor_score < 0.3 and entity_score > 0.7:
            # Crypto transactions ou casos onde vendor não aparece na descrição
            final_score = (
                amount_score * 0.45 +      # Aumentar peso do valor
                date_score * 0.25 +        # Aumentar peso da data
                vendor_score * 0.10 +      # Reduzir peso do vendor
                entity_score * 0.15 +      # Aumentar peso da entity
                pattern_score * 0.05       # Patterns como bônus
            )
        else:
            # Matching tradicional onde vendor é disponível
            final_score = (
                amount_score * 0.35 +      # Valor é muito importante
                date_score * 0.20 +        # Data é importante
                vendor_score * 0.25 +      # Vendor matching é crucial
                entity_score * 0.10 +      # Entity matching é útil
                pattern_score * 0.10       # Patterns são bônus
            )

        # Só retorna se score mínimo atingido
        if final_score < self.match_threshold_medium:
            return None

        # Determinar confidence level e auto-match
        if final_score >= self.match_threshold_high:
            confidence_level = "HIGH"
            auto_match = True
        elif final_score >= self.match_threshold_medium:
            confidence_level = "MEDIUM"
            auto_match = False
        else:
            confidence_level = "LOW"
            auto_match = False

        # Gerar explicação
        explanation = self._generate_match_explanation(criteria_scores, invoice, transaction)

        # Determinar tipo de match
        match_type = self._determine_match_type(criteria_scores)

        return MatchResult(
            invoice_id=invoice['id'],
            transaction_id=transaction['transaction_id'],
            score=final_score,
            match_type=match_type,
            criteria_scores=criteria_scores,
            confidence_level=confidence_level,
            explanation=explanation,
            auto_match=auto_match
        )

    def _calculate_amount_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """
        🚀 OTIMIZADO: Calcula score de matching por valor incluindo transações negativas
        Considera estornos, reembolsos e diferentes direções de pagamento
        """
        try:
            invoice_amount = float(invoice['total_amount'])
            transaction_amount = float(transaction['amount'])

            # Use absolute value for comparison but track if it's negative
            abs_transaction_amount = abs(transaction_amount)
            is_negative = transaction_amount < 0

            # Exact match (consider both positive and negative)
            if abs(invoice_amount - abs_transaction_amount) < 0.01:
                # Negative transactions might be refunds/cancellations - still valid matches
                return 1.0 if not is_negative else 0.95

            # Percentage difference
            diff_percentage = abs(invoice_amount - abs_transaction_amount) / invoice_amount

            # Base scoring
            base_score = 0.0
            if diff_percentage <= 0.01:  # 1%
                base_score = 0.98
            elif diff_percentage <= self.amount_tolerance:  # 3%
                base_score = 0.95
            elif diff_percentage <= 0.05:  # 5%
                base_score = 0.85
            elif diff_percentage <= 0.08:  # 8%
                base_score = 0.75
            elif diff_percentage <= 0.15:  # 15%
                base_score = 0.60
            elif diff_percentage <= 0.25:  # 25%
                base_score = 0.40
            else:
                return 0.0

            # Adjust for negative transactions (slightly lower but still valid)
            if is_negative and base_score > 0:
                base_score *= 0.90  # 10% penalty for negative amounts

            return base_score

        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0

    def _calculate_date_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """
        🚀 OTIMIZADO: Calcula score de matching por data com tolerância expandida
        🔒 REGRA DE NEGÓCIO: Invoice SEMPRE anterior à transação (pagamento)
        """
        try:
            # Parse dates
            invoice_date = datetime.strptime(invoice['date'], '%Y-%m-%d')
            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')

            # 🚨 REGRA CRÍTICA: Invoice deve ser anterior ao pagamento
            if invoice_date > transaction_date:
                logger.warning(f"TEMPORAL VIOLATION: Invoice {invoice.get('invoice_number', 'N/A')} "
                             f"dated {invoice_date.strftime('%Y-%m-%d')} is AFTER transaction "
                             f"dated {transaction_date.strftime('%Y-%m-%d')}")
                return 0.0  # Score zero para violações temporais

            # Use due date if available, otherwise invoice date
            due_date = invoice.get('due_date')
            if due_date:
                target_date = datetime.strptime(due_date, '%Y-%m-%d')
                # Due date também deve ser anterior ou igual à transação
                if target_date > transaction_date:
                    # Permitir pequena tolerância para due date (alguns dias)
                    days_after_due = (target_date - transaction_date).days
                    if days_after_due > 7:  # Máximo 7 dias de atraso no pagamento
                        return 0.0
            else:
                target_date = invoice_date

            # Calculate difference in days (transaction deve ser >= target_date)
            diff_days = (transaction_date - target_date).days

            # Realistic scoring - invoices são pagos em semanas/meses, não anos
            if diff_days == 0:
                return 1.0
            elif diff_days <= 3:
                return 0.95  # Mesmo período próximo
            elif diff_days <= 7:
                return 0.90  # Mesma semana
            elif diff_days <= 15:
                return 0.80  # Mesmo período quinzenal
            elif diff_days <= 30:
                return 0.70  # Mesmo mês
            elif diff_days <= 60:
                return 0.55  # Até 2 meses (normal)
            elif diff_days <= 90:
                return 0.40  # Até 3 meses (aceitável)
            elif diff_days <= 180:
                return 0.25  # Até 6 meses (possível para casos especiais)
            elif diff_days <= 365:
                return 0.10  # Até 1 ano (raro mas possível)
            else:
                return 0.02  # Mais de 1 ano (muito improvável)

        except (ValueError, TypeError):
            return 0.0

    def _calculate_vendor_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por vendor/descrição"""
        vendor_name = (invoice.get('vendor_name') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not vendor_name or not transaction_desc:
            return 0.0

        # Exact match
        if vendor_name in transaction_desc or transaction_desc in vendor_name:
            return 1.0

        # Fuzzy matching usando SequenceMatcher
        similarity = SequenceMatcher(None, vendor_name, transaction_desc).ratio()

        if similarity >= 0.8:
            return similarity
        elif similarity >= 0.6:
            return similarity * 0.8  # Penalize partial matches
        elif similarity >= 0.4:
            return similarity * 0.6
        else:
            # Try matching individual words
            vendor_words = set(vendor_name.split())
            desc_words = set(transaction_desc.split())

            if vendor_words & desc_words:  # Common words
                common_ratio = len(vendor_words & desc_words) / len(vendor_words)
                return min(common_ratio * 0.7, 0.6)

        return 0.0

    def _calculate_entity_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score de matching por business unit/entity"""
        invoice_vendor = (invoice.get('vendor_name') or '').lower().strip()
        transaction_entity = (transaction.get('classified_entity') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        # Melhorar reconhecimento de entidades Delta
        delta_indicators = [
            'delta mining paraguay s.a.',
            'delta mining paraguay',
            'delta mining',
            'delta',
            'tether transaction',  # Crypto payments para Delta
            'usdc transaction',    # Crypto payments para Delta
            'usd coin transaction' # Crypto payments para Delta
        ]

        # Se invoice é de Delta Mining Paraguay S.A., verificar se transação é relacionada
        if 'delta mining paraguay' in invoice_vendor:
            # Crypto transactions são geralmente para Delta Mining
            if any(indicator in transaction_desc for indicator in ['tether transaction', 'usdc transaction', 'usd coin transaction']):
                return 0.90  # Alta probabilidade de ser pagamento para Delta

            # Se entidade está como NEEDS REVIEW mas descrição sugere crypto, assumir Delta
            if transaction_entity == 'needs review' and 'transaction' in transaction_desc:
                return 0.85

            # Direct entity match
            if 'delta' in transaction_entity:
                return 1.0

        # Mapping expandido para entidades Delta
        entity_mapping = {
            'delta mining paraguay': ['delta', 'delta mining', 'mining', 'needs review'],
            'delta llc': ['delta', 'delta llc', 'llc'],
            'delta prop': ['delta prop', 'prop shop', 'prop'],
            'delta brazil': ['delta brazil', 'brazil', 'brasil']
        }

        # Check vendor to entity mapping
        for main_entity, variants in entity_mapping.items():
            if main_entity in invoice_vendor:
                if any(variant in transaction_entity for variant in variants):
                    return 0.85
                # Se transaction está como NEEDS REVIEW, dar benefit of doubt para Delta
                if transaction_entity == 'needs review':
                    return 0.70

        # Direct match
        if invoice_vendor and transaction_entity and invoice_vendor == transaction_entity:
            return 1.0

        # Se nenhuma info específica, mas transaction é crypto e invoice é Delta
        if 'delta' in invoice_vendor and 'transaction' in transaction_desc:
            return 0.60

        return 0.30  # Mais neutro que antes

    def _calculate_pattern_match_score(self, invoice: Dict, transaction: Dict) -> float:
        """Calcula score baseado em padrões (invoice number, etc.)"""
        invoice_number = (invoice.get('invoice_number') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not invoice_number or not transaction_desc:
            return 0.0

        # Look for invoice number in transaction description
        if invoice_number in transaction_desc:
            return 1.0

        # Look for numeric patterns
        invoice_numbers = re.findall(r'\d+', invoice_number)
        desc_numbers = re.findall(r'\d+', transaction_desc)

        for inv_num in invoice_numbers:
            if len(inv_num) >= 4 and inv_num in desc_numbers:  # Only significant numbers
                return 0.8

        return 0.0

    def _determine_match_type(self, criteria_scores: Dict[str, float]) -> str:
        """Determina o tipo principal de match baseado nos scores"""
        max_score = max(criteria_scores.values())
        max_criterion = max(criteria_scores, key=criteria_scores.get)

        type_mapping = {
            'amount': 'AMOUNT_MATCH',
            'vendor': 'VENDOR_MATCH',
            'pattern': 'PATTERN_MATCH',
            'date': 'DATE_MATCH',
            'entity': 'ENTITY_MATCH'
        }

        return type_mapping.get(max_criterion, 'COMBINED_MATCH')

    def _generate_match_explanation(self, criteria_scores: Dict[str, float],
                                  invoice: Dict, transaction: Dict) -> str:
        """Gera explicação textual do porquê do match"""
        explanations = []

        if criteria_scores['amount'] >= 0.9:
            explanations.append(f"Valor exato/muito próximo ({invoice['total_amount']} ≈ {transaction['amount']})")
        elif criteria_scores['amount'] >= 0.7:
            explanations.append(f"Valor compatível ({invoice['total_amount']} ~ {transaction['amount']})")

        if criteria_scores['vendor'] >= 0.8:
            explanations.append(f"Vendor match: '{invoice.get('vendor_name', '')}' em '{transaction.get('description', '')}'")

        if criteria_scores['date'] >= 0.8:
            explanations.append(f"Data próxima ao vencimento ({invoice.get('due_date', invoice['date'])} ~ {transaction['date']})")

        if criteria_scores['pattern'] >= 0.8:
            explanations.append(f"Invoice# {invoice.get('invoice_number', '')} encontrado na descrição")

        if criteria_scores['entity'] >= 0.8:
            explanations.append(f"Mesmo business unit ({invoice.get('business_unit', '')})")

        return " | ".join(explanations) if explanations else "Match baseado em múltiplos critérios"

    def apply_semantic_matching(self, matches: List[MatchResult],
                              invoices: List[Dict], transactions: List[Dict]) -> List[MatchResult]:
        """
        🚀 OTIMIZADO: Aplica matching semântico com IA usando:
        - Smart filtering (IA apenas para scores 0.4-0.8)
        - Batch processing (15-20 matches por chamada)
        - Paralelização (3 threads simultâneas)
        - Sanitização de dados
        """
        if not self.claude_client:
            logger.warning("Claude client not available - skipping AI evaluation")
            return matches

        if not matches:
            return matches

        # Initialize progress tracking
        self.start_time = time.time()
        self.current_progress = 0

        # 1. SMART FILTERING - IA apenas para casos ambíguos (0.4-0.8)
        ai_candidates = []
        auto_approved = []
        auto_rejected = []

        for match in matches:
            if match.score >= self.ai_filter_threshold_high:
                # Score alto (≥0.8) - AUTO APROVADO
                auto_approved.append(match)
            elif match.score >= self.ai_filter_threshold_low:
                # Score ambíguo (0.4-0.8) - ENVIAR PARA IA
                ai_candidates.append(match)
            else:
                # Score baixo (<0.4) - AUTO REJEITADO
                auto_rejected.append(match)

        self.total_progress = len(ai_candidates)

        logger.info(f"🧠 SMART AI FILTERING: {len(ai_candidates)} ambiguous cases for AI analysis")
        logger.info(f"✅ Auto-approved: {len(auto_approved)} (score ≥{self.ai_filter_threshold_high})")
        logger.info(f"❌ Auto-rejected: {len(auto_rejected)} (score <{self.ai_filter_threshold_low})")

        if not ai_candidates:
            logger.info("🚀 NO AI PROCESSING NEEDED - All matches filtered automatically!")
            return auto_approved + auto_rejected

        # 2. BATCH PROCESSING + PARALELIZAÇÃO para casos ambíguos
        logger.info(f"🚀 BATCH PROCESSING: {len(ai_candidates)} matches in {self.batch_size}-match batches")

        enhanced_matches = []
        batches = [ai_candidates[i:i + self.batch_size] for i in range(0, len(ai_candidates), self.batch_size)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(self._process_batch_with_ai, batch, invoices, transactions): batch
                for batch in batches
            }

            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    enhanced_matches.extend(batch_results)
                except Exception as e:
                    batch = future_to_batch[future]
                    logger.error(f"Error processing batch: {e}")
                    enhanced_matches.extend(batch)  # Keep originals if batch fails

        # Combine all results
        all_matches = auto_approved + enhanced_matches + auto_rejected

        elapsed = time.time() - self.start_time
        logger.info(f"🚀 OPTIMIZATION COMPLETE: {len(ai_candidates)} AI evaluations in {elapsed:.1f}s")
        logger.info(f"⚡ Performance: {len(ai_candidates)/elapsed:.1f} matches/second")

        return all_matches

    def _process_batch_with_ai(self, batch: List[MatchResult],
                              invoices: List[Dict], transactions: List[Dict]) -> List[MatchResult]:
        """🚀 Processa um lote de matches usando Claude AI com dados sanitizados"""
        if not batch:
            return []

        # Build batch prompt with sanitized data
        batch_data = []
        for i, match in enumerate(batch):
            invoice = next((inv for inv in invoices if inv['id'] == match.invoice_id), None)
            transaction = next((txn for txn in transactions if txn['transaction_id'] == match.transaction_id), None)

            if invoice and transaction:
                batch_data.append({
                    "match_id": i,
                    "invoice": {
                        "number": self._sanitize_text(str(invoice.get('invoice_number', 'N/A'))),
                        "vendor": self._sanitize_text(str(invoice.get('vendor_name', 'N/A'))),
                        "amount": float(invoice.get('total_amount', 0)),
                        "currency": self._sanitize_text(str(invoice.get('currency', 'USD'))),
                        "date": self._sanitize_text(str(invoice.get('date', 'N/A'))),
                        "due_date": self._sanitize_text(str(invoice.get('due_date', 'N/A')))
                    },
                    "transaction": {
                        "description": self._sanitize_text(str(transaction.get('description', 'N/A'))),
                        "amount": float(transaction.get('amount', 0)),
                        "currency": self._sanitize_text(str(transaction.get('currency', 'USD'))),
                        "date": self._sanitize_text(str(transaction.get('date', 'N/A'))),
                        "entity": self._sanitize_text(str(transaction.get('classified_entity', 'N/A')))
                    },
                    "current_score": round(match.score, 3)
                })

        if not batch_data:
            return batch

        prompt = f"""
        Você é o AVALIADOR PRINCIPAL de revenue recognition. Analise este lote de {len(batch_data)} invoice-transaction pairs:

        {json.dumps(batch_data, indent=2)}

        INSTRUÇÕES CRÍTICAS:
        1. 🚨 REGRA TEMPORAL OBRIGATÓRIA: Invoice SEMPRE deve ser anterior à transação (pagamento)
           - Se invoice_date > transaction_date: AUTOMATICAMENTE REJEITAR (is_match: false)
           - Se due_date > transaction_date por mais de 7 dias: REJEITAR
        2. Para Delta Mining Paraguay S.A.: Transações crypto (USDT, USDC) são pagamentos típicos
        3. Pequenas diferenças de valor (até 5%) são normais (taxas, timing)
        4. Datas próximas (1-5 dias) são aceitáveis APENAS se respeitarem regra temporal
        5. "NEEDS REVIEW" em entity é comum para crypto transactions

        Para cada match, decida se é válido e ajuste o score se necessário.

        Responda em JSON:
        {{
            "evaluations": [
                {{
                    "match_id": 0,
                    "is_match": true/false,
                    "confidence": 0.0-1.0,
                    "adjusted_score": 0.0-1.0,
                    "reasoning": "explicação concisa"
                }}
            ]
        }}
        """

        try:
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            evaluations = result.get('evaluations', [])

            enhanced_batch = []
            for i, match in enumerate(batch):
                eval_result = next((e for e in evaluations if e.get('match_id') == i), None)

                if eval_result and eval_result.get('is_match', False) and eval_result.get('confidence', 0) > 0.6:
                    # AI aprova o match
                    ai_score = min(eval_result.get('adjusted_score', match.score), 0.98)
                    enhanced_match = MatchResult(
                        invoice_id=match.invoice_id,
                        transaction_id=match.transaction_id,
                        score=ai_score,
                        match_type=f"AI_BATCH_{match.match_type}",
                        criteria_scores=match.criteria_scores,
                        confidence_level="HIGH" if ai_score >= 0.85 else "MEDIUM",
                        explanation=f"🤖 AI BATCH: {eval_result.get('reasoning', '')}",
                        auto_match=ai_score >= 0.85
                    )
                    enhanced_batch.append(enhanced_match)
                else:
                    # AI rejeita ou baixa confiança
                    rejected_score = max(match.score * 0.5, 0.2)
                    enhanced_match = MatchResult(
                        invoice_id=match.invoice_id,
                        transaction_id=match.transaction_id,
                        score=rejected_score,
                        match_type=f"AI_BATCH_REJECTED_{match.match_type}",
                        criteria_scores=match.criteria_scores,
                        confidence_level="LOW",
                        explanation=f"🤖 AI BATCH REJECTED: {eval_result.get('reasoning', 'Low confidence') if eval_result else 'AI analysis failed'}",
                        auto_match=False
                    )
                    enhanced_batch.append(enhanced_match)

            # Update progress
            self.update_progress(self.current_progress + len(batch))
            return enhanced_batch

        except Exception as e:
            logger.error(f"Error in batch AI processing: {e}")
            return batch  # Return original batch if AI fails

    def _enhance_match_with_ai(self, match: MatchResult,
                             invoices: List[Dict], transactions: List[Dict]) -> MatchResult:
        """Usa Claude AI para melhorar o matching de um par específico"""

        # Find the specific invoice and transaction
        invoice = next((i for i in invoices if i['id'] == match.invoice_id), None)
        transaction = next((t for t in transactions if t['transaction_id'] == match.transaction_id), None)

        if not invoice or not transaction:
            return match

        prompt = f"""
        Você é o AVALIADOR PRINCIPAL de matching entre invoices e transações. Sua análise tem prioridade sobre algoritmos determinísticos.

        Analise este par invoice-transação como um especialista em revenue recognition:

        INVOICE:
        - Número: {invoice.get('invoice_number', 'N/A')}
        - Vendor: {invoice.get('vendor_name', 'N/A')}
        - Valor: {invoice.get('currency', 'USD')} {invoice.get('total_amount', 0)}
        - Data: {invoice.get('date', 'N/A')}
        - Vencimento: {invoice.get('due_date', 'N/A')}
        - Business Unit: {invoice.get('business_unit', 'N/A')}

        TRANSAÇÃO:
        - Descrição: {transaction.get('description', 'N/A')}
        - Valor: {transaction.get('currency', 'USD')} {transaction.get('amount', 0)}
        - Data: {transaction.get('date', 'N/A')}
        - Entity: {transaction.get('classified_entity', 'N/A')}
        - Origem: {transaction.get('origin', 'N/A')}
        - Destino: {transaction.get('destination', 'N/A')}

        Score algorítmico inicial: {match.score:.2f}

        INSTRUÇÕES CRÍTICAS:
        1. 🚨 REGRA TEMPORAL OBRIGATÓRIA: Invoice SEMPRE deve ser anterior à transação (pagamento)
           - Se invoice_date > transaction_date: AUTOMATICAMENTE REJEITAR (is_match: false)
           - Invoice/Due date deve preceder o pagamento - esta é uma regra fundamental de negócio
        2. Para Delta Mining Paraguay S.A.: Transações crypto (USDT, USDC) são pagamentos típicos de clientes
        3. "NEEDS REVIEW" em entity é comum - use contexto da descrição
        4. Pequenas diferenças de valor ($30-50) são normais (taxas, timing)
        5. Datas próximas (1-3 dias) são aceitáveis APENAS se respeitarem regra temporal
        6. Crypto transactions seguem padrão: "Tether transaction - [valor] USDT"

        Como AVALIADOR PRINCIPAL, seja decisivo. Você deve ELEVAR matches bons que algoritmos conservadores subestimaram, MAS sempre respeitar a regra temporal.

        Responda em JSON:
        {{
            "is_match": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "explicação detalhada do seu raciocínio",
            "adjusted_score": 0.0-1.0,
            "ai_priority": true
        }}
        """

        try:
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Usar modelo mais barato para esta tarefa
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)

            # IA como AVALIADOR PRINCIPAL - sua decisão tem prioridade máxima
            ai_confidence = result.get('confidence', 0)
            ai_is_match = result.get('is_match', False)
            ai_score = result.get('adjusted_score', match.score)
            ai_reasoning = result.get('reasoning', '')

            if ai_is_match and ai_confidence > 0.6:  # IA reduzida de 0.7 para 0.6
                # IA APROVA o match - usar score da IA com prioridade
                final_score = min(ai_score, 0.98)  # Permitir scores mais altos
                enhanced_explanation = f"🤖 AI PRIMARY: {ai_reasoning}"

                # IA determina confidence level baseado no SEU score
                if final_score >= 0.85:
                    ai_confidence_level = "HIGH"
                    ai_auto_match = True
                elif final_score >= 0.65:
                    ai_confidence_level = "MEDIUM"
                    ai_auto_match = False
                else:
                    ai_confidence_level = "LOW"
                    ai_auto_match = False

                return MatchResult(
                    invoice_id=match.invoice_id,
                    transaction_id=match.transaction_id,
                    score=final_score,
                    match_type=f"AI_PRIMARY_{match.match_type}",
                    criteria_scores=match.criteria_scores,
                    confidence_level=ai_confidence_level,
                    explanation=enhanced_explanation,
                    auto_match=ai_auto_match
                )
            else:
                # IA REJEITA o match - reduzir score drasticamente
                rejected_score = max(match.score * 0.5, 0.2)  # Penalidade maior
                return MatchResult(
                    invoice_id=match.invoice_id,
                    transaction_id=match.transaction_id,
                    score=rejected_score,
                    match_type=f"AI_REJECTED_{match.match_type}",
                    criteria_scores=match.criteria_scores,
                    confidence_level="LOW",
                    explanation=f"🤖 AI REJECTED: {ai_reasoning}",
                    auto_match=False
                )

        except Exception as e:
            logger.error(f"Error in Claude API call: {e}")
            return match

    def save_match_results(self, matches: List[MatchResult], auto_apply: bool = False) -> Dict[str, int]:
        """
        Salva resultados de matching no banco de dados

        Args:
            matches: Lista de matches encontrados
            auto_apply: Se True, aplica automaticamente matches com high confidence

        Returns:
            Dict com estatísticas de quantos matches foram aplicados, salvos para revisão, etc.
        """
        stats = {
            'auto_applied': 0,
            'pending_review': 0,
            'total_processed': 0
        }

        for match in matches:
            try:
                if auto_apply and match.auto_match:
                    # Apply match automatically
                    self._apply_match(match)
                    stats['auto_applied'] += 1
                else:
                    # Save for manual review
                    self._save_pending_match(match)
                    stats['pending_review'] += 1

                stats['total_processed'] += 1

            except Exception as e:
                logger.error(f"Error saving match {match.invoice_id}-{match.transaction_id}: {e}")

        logger.info(f"Processed {stats['total_processed']} matches: "
                   f"{stats['auto_applied']} auto-applied, {stats['pending_review']} pending review")

        return stats

    def _apply_match(self, match: MatchResult):
        """
        🔗 APLICA LINKING BIDIRECIONAL + AI ENRICHMENT - Atualiza AMBAS as tabelas e enriquece transação
        invoice.linked_transaction_id E transaction.invoice_id + AI categories
        """
        try:
            # 1. Atualizar INVOICE com linked_transaction_id (no updated_at column)
            invoice_query = """
                UPDATE invoices
                SET linked_transaction_id = ?,
                    status = 'paid'
                WHERE id = ?
            """

            # 2. Atualizar TRANSACTION com invoice_id (NOVO!)
            transaction_query = """
                UPDATE transactions
                SET invoice_id = ?
                WHERE transaction_id = ?
            """

            if db_manager.db_type == 'postgresql':
                invoice_query = invoice_query.replace('?', '%s')
                transaction_query = transaction_query.replace('?', '%s')

            # Executar AMBAS as atualizações para linking bidirecional
            db_manager.execute_query(invoice_query, (match.transaction_id, match.invoice_id))
            db_manager.execute_query(transaction_query, (match.invoice_id, match.transaction_id))

            logger.info(f"🔗 BIDIRECTIONAL LINK: Invoice {match.invoice_id} ↔ Transaction {match.transaction_id}")

            # 3. 🤖 AI ENRICHMENT AUTOMÁTICO: Enriquecer transação com contexto da invoice
            try:
                # Buscar dados da invoice para enrichment
                invoice_data = db_manager.execute_query("""
                    SELECT vendor_name, customer_name, invoice_number, total_amount, category, business_unit
                    FROM invoices
                    WHERE id = %s
                """ if db_manager.db_type == 'postgresql' else """
                    SELECT vendor_name, customer_name, invoice_number, total_amount, category, business_unit
                    FROM invoices
                    WHERE id = ?
                """, (match.invoice_id,), fetch_one=True)

                if invoice_data:
                    logger.info(f"🤖 AUTO-MATCH AI ENRICHMENT: Starting for transaction {match.transaction_id}")
                    # TEMPORARILY DISABLED: Runtime import causes generator issues
                    # from app_db import enrich_transaction_with_invoice_context
                    # enrichment_success = enrich_transaction_with_invoice_context(match.transaction_id, invoice_data)
                    # if enrichment_success:
                    #     logger.info(f"🤖 AUTO-MATCH AI SUCCESS: Enriched transaction {match.transaction_id} with invoice context")
                    # else:
                    #     logger.warning(f"🤖 AUTO-MATCH AI FAILED: Could not enrich transaction {match.transaction_id}")
                    logger.info(f"🤖 AUTO-MATCH: Enrichment disabled to prevent generator errors")
                else:
                    logger.warning(f"🤖 AUTO-MATCH: Could not retrieve invoice data for enrichment: {match.invoice_id}")
            except Exception as e:
                logger.warning(f"🤖 AUTO-MATCH: AI enrichment failed (non-critical): {e}")
                # Don't fail the match application due to enrichment errors

            # Log the automatic match
            self._log_match_action(match, 'AUTO_APPLIED', 'System')

        except Exception as e:
            logger.error(f"❌ Error applying bidirectional match: {e}")
            raise

    def _save_pending_match(self, match: MatchResult):
        """Salva match para revisão manual"""
        # Create pending matches table if not exists
        self._ensure_pending_matches_table()

        query = """
            INSERT INTO pending_invoice_matches
            (invoice_id, transaction_id, score, match_type, criteria_scores,
             confidence_level, explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        db_manager.execute_query(query, (
            match.invoice_id,
            match.transaction_id,
            match.score,
            match.match_type,
            json.dumps(match.criteria_scores),
            match.confidence_level,
            match.explanation
        ))

    def _ensure_pending_matches_table(self):
        """Garante que a tabela de matches pendentes existe"""
        if db_manager.db_type == 'postgresql':
            query = """
                CREATE TABLE IF NOT EXISTS pending_invoice_matches (
                    id SERIAL PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    score DECIMAL(3,2) NOT NULL,
                    match_type TEXT NOT NULL,
                    criteria_scores JSONB,
                    confidence_level TEXT NOT NULL,
                    explanation TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(invoice_id, transaction_id)
                )
            """
        else:
            query = """
                CREATE TABLE IF NOT EXISTS pending_invoice_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    match_type TEXT NOT NULL,
                    criteria_scores TEXT,
                    confidence_level TEXT NOT NULL,
                    explanation TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(invoice_id, transaction_id)
                )
            """

        db_manager.execute_query(query)

    def _log_match_action(self, match: MatchResult, action: str, user: str):
        """Registra ações de matching para auditoria"""
        # Create log table if not exists
        self._ensure_match_log_table()

        query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        if db_manager.db_type == 'postgresql':
            query = query.replace('?', '%s')

        try:
            db_manager.execute_query(query, (
                match.invoice_id,
                match.transaction_id,
                action,
                match.score,
                match.match_type,
                user
            ))
        except Exception as e:
            logger.error(f"Error logging match action: {e}")

    def _ensure_match_log_table(self):
        """Garante que a tabela de log existe"""
        if db_manager.db_type == 'postgresql':
            query = """
                CREATE TABLE IF NOT EXISTS invoice_match_log (
                    id SERIAL PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    score DECIMAL(3,2),
                    match_type TEXT,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            query = """
                CREATE TABLE IF NOT EXISTS invoice_match_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    score REAL,
                    match_type TEXT,
                    user_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """

        db_manager.execute_query(query)

# Convenience function for external use
def run_invoice_matching(invoice_ids: List[str] = None, auto_apply: bool = False) -> Dict[str, Any]:
    """
    Função principal para executar matching de invoices

    Args:
        invoice_ids: Lista específica de invoices para processar
        auto_apply: Se deve aplicar automaticamente matches de alta confiança

    Returns:
        Dict com resultados e estatísticas
    """
    matcher = RevenueInvoiceMatcher()

    # Find matches
    matches = matcher.find_matches_for_invoices(invoice_ids)

    # Apply semantic matching to improve ambiguous cases
    if matches:
        # Get full data for semantic matching
        invoices = matcher._get_unmatched_invoices(invoice_ids)
        transactions = matcher._get_candidate_transactions()
        matches = matcher.apply_semantic_matching(matches, invoices, transactions)

    # Save results
    stats = matcher.save_match_results(matches, auto_apply)

    return {
        'success': True,
        'total_matches': len(matches),
        'high_confidence': len([m for m in matches if m.confidence_level == 'HIGH']),
        'medium_confidence': len([m for m in matches if m.confidence_level == 'MEDIUM']),
        'auto_applied': stats['auto_applied'],
        'pending_review': stats['pending_review'],
        'matches': [
            {
                'invoice_id': m.invoice_id,
                'transaction_id': m.transaction_id,
                'score': m.score,
                'match_type': m.match_type,
                'confidence_level': m.confidence_level,
                'explanation': m.explanation,
                'auto_match': m.auto_match
            }
            for m in matches
        ]
    }
