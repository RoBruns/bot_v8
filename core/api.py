import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MAX_RETRIES = 25
TIMEOUT_SECONDS = 10

URL_AUTH_TOKEN      = 'https://auth.v8sistema.com/oauth/token'
URL_CONSULT_BALANCE = 'https://bff.v8sistema.com/fgts/balance'
URL_SIMULATION      = 'https://bff.v8sistema.com/fgts/simulations'

AUTH_AUDIENCE   = 'https://bff.v8sistema.com'
AUTH_CLIENT_ID  = 'DHWogdaYmEI8n5bwwxPDzulMlSK7dwIn'
AUTH_SCOPE      = 'offline_access'
AUTH_GRANT_TYPE = 'password'
PROVIDER_BMS    = "bms"

TABELAS = {
    "1": {"nome": "Normal", "id": "cb563029-ba93-4b53-8d53-4ac145087212"},
    "2": {"nome": "Cometa", "id": "61c9fb2f-c902-4992-b8f5-b0ee368c45b0"},
}


class ConsultStatus(str, Enum):
    NAO_AUTORIZADO = "NAO AUTORIZADO"
    SEM_SALDO      = "SEM SALDO"
    CPF_INVALIDO   = "CPF INVÁLIDO"
    FALHA_CONSULTA = "FALHA CONSULTA"
    RETRY          = "RETRY"
    TOKEN_EXPIRADO = "TOKEN EXPIRADO"


def get_token(username: str, password: str) -> Optional[str]:
    data = {
        'grant_type': AUTH_GRANT_TYPE,
        'username': username,
        'password': password,
        'audience': AUTH_AUDIENCE,
        'scope': AUTH_SCOPE,
        'client_id': AUTH_CLIENT_ID,
    }
    try:
        r = requests.post(URL_AUTH_TOKEN, data=data, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        return r.json().get('access_token')
    except requests.RequestException as e:
        logging.error(f"Erro ao obter token: {e}")
        return None


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def _handle_consult_error(response: requests.Response, cpf: str) -> Tuple[Any, Any, bool, Optional[str]]:
    try:
        raw = response.text
        try:
            body = response.json()
        except ValueError:
            logging.warning(f"CPF {cpf}: resposta não-JSON ({response.status_code}): {raw[:200]}")
            return ConsultStatus.RETRY, None, False, None
        error_msg = str(body.get('error', ''))

        if response.status_code == 400:
            detail = body.get('detail', '')
            if "não possui autorização" in detail or "Instituição Fiduciária" in detail:
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if "não possui saldo disponível" in detail.lower():
                return ConsultStatus.SEM_SALDO, None, True, None
            return None, None, False, f"HTTP 400: {detail or error_msg}"

        if response.status_code == 500:
            if error_msg in ('values() must be called with at least one value',
                             "Saldo insuficiente, parcelas menores R$10,00."):
                return ConsultStatus.SEM_SALDO, None, True, None
            if error_msg == "Cannot read properties of undefined (reading 'map')":
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if any(x in error_msg for x in [
                "Falha ao buscar o saldo disponivel!",
                "Serviço indisponivel no momento, tente novamente mais tarde",
                "Excedido o limite de requisições (máximo de 1 por segundo).",
                "Limite de requisições excedido, tente novamente mais tarde",
            ]):
                return ConsultStatus.RETRY, None, False, None
            if any(x in error_msg for x in ["Instituição Fiduciária", "Cliente não autorizou", "Empty response"]):
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if "Número de CPF inválido" in error_msg:
                return ConsultStatus.CPF_INVALIDO, None, True, None
            if "Valor dos custos superior ao valor financiado" in error_msg or "Saldo insuficiente" in error_msg:
                return ConsultStatus.SEM_SALDO, None, True, None
            logging.error(f"Erro 500 desconhecido CPF {cpf}: {error_msg}")
            return None, None, False, f"HTTP 500: {error_msg}"

        return None, None, False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return None, None, False, f"Erro ao processar resposta: {e}"


def consult_balance(
    session: requests.Session, token: str, cpf: str, averbador: str
) -> Tuple[Optional[List[Dict]], Optional[str], bool, Optional[str]]:
    headers = {'Authorization': f'Bearer {token}'}
    data = {"documentNumber": cpf, "provider": averbador}
    params = {"search": cpf, "status": "success", "page": 1, "limit": 1}

    retries = 0
    while retries < MAX_RETRIES:
        try:
            r = session.post(URL_CONSULT_BALANCE, headers=headers, json=data, timeout=TIMEOUT_SECONDS)
            r.raise_for_status()
            balance_data = r.json()

            if balance_data is None:
                poll = 0
                while poll < 15:
                    r = session.get(URL_CONSULT_BALANCE, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
                    r.raise_for_status()
                    balance_data = r.json()
                    if balance_data and balance_data.get('data'):
                        break
                    time.sleep(2)
                    poll += 1

            if not balance_data:
                return None, None, False, "Resposta nula após polling"

            data_list = balance_data.get('data', [])
            if not data_list:
                return None, None, False, "data vazio após polling"

            first = data_list[0]
            periods = first.get('periods', [])
            balance_id = first.get('id')

            if not isinstance(periods, list):
                return None, None, False, "balance_periods inválido"

            new_periods = [
                {"totalAmount": a['amount'], "amount": a['amount'], "dueDate": a['dueDate']}
                for a in periods if isinstance(a, dict)
            ]
            return new_periods, balance_id, True, None

        except requests.RequestException as e:
            if getattr(e.response, 'status_code', None) == 429:
                time.sleep(2)
                retries += 1
                continue
            if e.response is not None:
                if e.response.status_code == 401:
                    return ConsultStatus.TOKEN_EXPIRADO, None, False, None
                result, b_id, finished, reason = _handle_consult_error(e.response, cpf)
                if result == ConsultStatus.RETRY:
                    time.sleep(0.4)
                    retries += 1
                    continue
                if finished:
                    return result, b_id, True, None
                return None, None, False, reason
            time.sleep(2)
            retries += 1
            continue
        except Exception as e:
            logging.error(f"Exceção consulta CPF {cpf}: {e}", exc_info=True)
            retries += 1
            continue

    return None, None, False, "Máximo de tentativas atingido"


def simulation(
    session: requests.Session, token: str, list_balance: List[Dict],
    cpf: str, balance_id: str, fees_id: str
) -> Optional[float]:
    headers = {'Authorization': f'Bearer {token}'}
    data = {
        "documentNumber": cpf,
        "isInsured": False,
        "simulationFeesId": fees_id,
        "targetAmount": 0,
        "provider": PROVIDER_BMS,
        "desiredInstallments": list_balance,
        "balanceId": balance_id,
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            r = session.post(URL_SIMULATION, headers=headers, json=data, timeout=TIMEOUT_SECONDS)
            if r.status_code >= 400:
                try:
                    body = r.json()
                    logging.error(f"CPF {cpf}: erro simulação ({r.status_code}): {body.get('error') or body.get('detail')}")
                except ValueError:
                    pass
                if r.status_code in (500, 502, 503, 504):
                    time.sleep(2)
                    retries += 1
                    continue
                r.raise_for_status()
            sim = r.json()
            return sim.get('availableBalance')
        except requests.RequestException as e:
            if getattr(e.response, 'status_code', None) == 429:
                time.sleep(2)
                retries += 1
                continue
            if getattr(e, 'response', None) is None:
                time.sleep(2)
                retries += 1
                continue
            logging.error(f"Erro fatal simulação CPF {cpf}: {e}")
            break

    return None


def process_cpf(
    cpf: str, token: str, session: requests.Session, fees_id: str
) -> Tuple[str, Union[str, float, ConsultStatus], Optional[str]]:
    time.sleep(2)
    balance, balance_id, success, reason = consult_balance(session, token, cpf, PROVIDER_BMS)

    if balance == ConsultStatus.TOKEN_EXPIRADO:
        return cpf, ConsultStatus.TOKEN_EXPIRADO, None

    if success and balance in (ConsultStatus.NAO_AUTORIZADO, ConsultStatus.CPF_INVALIDO):
        return cpf, balance.value, None

    if success and balance not in (ConsultStatus.SEM_SALDO, None):
        if len(balance) < 2:
            return cpf, ConsultStatus.SEM_SALDO.value, None
        sim = simulation(session, token, balance, cpf, balance_id, fees_id)
        if sim is not None:
            return cpf, sim, None
        return cpf, ConsultStatus.FALHA_CONSULTA.value, "Simulação não retornou saldo"

    if not success:
        return cpf, ConsultStatus.FALHA_CONSULTA.value, reason

    return cpf, ConsultStatus.SEM_SALDO.value, None
