from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from models import EventoCreate, EventoUpdate, EventoResponse, ResumoEvento
from auth import get_current_admin_user, get_current_user
from database import execute_query, get_db_connection

router = APIRouter(prefix="/eventos", tags=["Eventos"])

@router.get("/", response_model=List[EventoResponse])
async def listar_eventos(
    current_user: dict = Depends(get_current_user)
):
    """Lista todos os eventos"""
    
    query = """
        SELECT id, data_evento, status, data_limite, data_criacao
        FROM eventos
        ORDER BY data_evento DESC
    """
    
    results = execute_query(query)
    
    return [
        EventoResponse(
            id=row["ID"],
            data_evento=row["DATA_EVENTO"],
            status=row["STATUS"],
            data_limite=row["DATA_LIMITE"],
            data_criacao=row["DATA_CRIACAO"]
        )
        for row in results
    ]

@router.get("/ativo", response_model=EventoResponse)
async def obter_evento_ativo(
    current_user: dict = Depends(get_current_user)
):
    """Obtém o evento atualmente aberto para pedidos"""
    
    query = """
        SELECT id, data_evento, status, data_limite, data_criacao
        FROM eventos
        WHERE status = 'ABERTO' AND data_limite > SYSTIMESTAMP
        ORDER BY data_evento DESC
        FETCH FIRST 1 ROWS ONLY
    """
    
    result = execute_query(query, fetch_one=True)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não há evento ativo no momento"
        )
    
    return EventoResponse(
        id=result[0],
        data_evento=result[1],
        status=result[2],
        data_limite=result[3],
        data_criacao=result[4]
    )

@router.get("/{evento_id}", response_model=EventoResponse)
async def obter_evento(
    evento_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Obtém um evento específico"""
    
    query = """
        SELECT id, data_evento, status, data_limite, data_criacao
        FROM eventos
        WHERE id = :evento_id
    """
    
    result = execute_query(query, {"evento_id": evento_id}, fetch_one=True)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    return EventoResponse(
        id=result[0],
        data_evento=result[1],
        status=result[2],
        data_limite=result[3],
        data_criacao=result[4]
    )

@router.post("/", response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
async def criar_evento(
    evento: EventoCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """Cria um novo evento (apenas admin)"""
    
    # Verificar se já existe evento para esta data
    check_query = "SELECT id FROM eventos WHERE data_evento = :data"
    existing = execute_query(check_query, {"data": evento.data_evento}, fetch_one=True)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um evento para esta data"
        )
    
    # Inserir evento
    insert_query = """
        INSERT INTO eventos (data_evento, data_limite, status)
        VALUES (:data_evento, :data_limite, 'ABERTO')
    """
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            insert_query,
            {
                "data_evento": evento.data_evento,
                "data_limite": evento.data_limite
            }
        )
        conn.commit()
        
        # Buscar evento criado
        select_query = """
            SELECT id, data_evento, status, data_limite, data_criacao
            FROM eventos
            WHERE data_evento = :data_evento
        """
        cursor.execute(select_query, {"data_evento": evento.data_evento})
        result = cursor.fetchone()
        cursor.close()
    
    return EventoResponse(
        id=result[0],
        data_evento=result[1],
        status=result[2],
        data_limite=result[3],
        data_criacao=result[4]
    )

@router.put("/{evento_id}", response_model=EventoResponse)
async def atualizar_evento(
    evento_id: int,
    evento: EventoUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """Atualiza um evento (apenas admin)"""
    
    # Verificar se evento existe
    check_query = "SELECT id FROM eventos WHERE id = :evento_id"
    existing = execute_query(check_query, {"evento_id": evento_id}, fetch_one=True)
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    # Construir query de atualização
    updates = []
    params = {"evento_id": evento_id}
    
    if evento.status is not None:
        updates.append("status = :status")
        params["status"] = evento.status
    
    if evento.data_limite is not None:
        updates.append("data_limite = :data_limite")
        params["data_limite"] = evento.data_limite
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    update_query = f"""
        UPDATE eventos
        SET {', '.join(updates)}
        WHERE id = :evento_id
    """
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(update_query, params)
        conn.commit()
        
        # Buscar evento atualizado
        select_query = """
            SELECT id, data_evento, status, data_limite, data_criacao
            FROM eventos
            WHERE id = :evento_id
        """
        cursor.execute(select_query, {"evento_id": evento_id})
        result = cursor.fetchone()
        cursor.close()
    
    return EventoResponse(
        id=result[0],
        data_evento=result[1],
        status=result[2],
        data_limite=result[3],
        data_criacao=result[4]
    )

@router.get("/{evento_id}/resumo", response_model=ResumoEvento)
async def obter_resumo_evento(
    evento_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """Obtém resumo completo de um evento (apenas admin)"""
    
    # Buscar dados do evento
    evento_query = """
        SELECT id, data_evento, status, data_limite, data_criacao
        FROM eventos
        WHERE id = :evento_id
    """
    evento_result = execute_query(evento_query, {"evento_id": evento_id}, fetch_one=True)
    
    if not evento_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado"
        )
    
    # Buscar estatísticas
    stats_query = """
        SELECT 
            COUNT(DISTINCT p.usuario_id) as total_participantes,
            COUNT(p.id) as total_pedidos,
            SUM(p.valor_total + p.valor_frete) as valor_total,
            SUM(ip.quantidade) as total_pedacos
        FROM pedidos p
        LEFT JOIN itens_pedido ip ON p.id = ip.pedido_id
        WHERE p.evento_id = :evento_id
    """
    stats_result = execute_query(stats_query, {"evento_id": evento_id}, fetch_one=True)
    
    total_participantes = int(stats_result[0]) if stats_result[0] else 0
    total_pedidos = int(stats_result[1]) if stats_result[1] else 0
    valor_total = float(stats_result[2]) if stats_result[2] else 0.0
    total_pedacos = int(stats_result[3]) if stats_result[3] else 0
    total_pizzas = total_pedacos // 8
    
    return ResumoEvento(
        evento=EventoResponse(
            id=evento_result[0],
            data_evento=evento_result[1],
            status=evento_result[2],
            data_limite=evento_result[3],
            data_criacao=evento_result[4]
        ),
        total_participantes=total_participantes,
        total_pedidos=total_pedidos,
        total_pizzas=total_pizzas,
        valor_total=valor_total
    )

@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_evento(
    evento_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """Deleta um evento (apenas admin)"""
    
    # Verificar se há pedidos no evento
    check_pedidos = """
        SELECT COUNT(*) FROM pedidos WHERE evento_id = :evento_id
    """
    result = execute_query(check_pedidos, {"evento_id": evento_id}, fetch_one=True)
    
    if result[0] > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível deletar evento com {result[0]} pedido(s). Delete os pedidos primeiro."
        )
    
    delete_query = "DELETE FROM eventos WHERE id = :evento_id"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(delete_query, {"evento_id": evento_id})
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento não encontrado"
            )
        
        conn.commit()
        cursor.close()
    
    return None