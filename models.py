from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date

# Modelos de Usuário
class UsuarioBase(BaseModel):
    nome_completo: str = Field(..., min_length=3, max_length=200)
    setor: str = Field(..., min_length=2, max_length=100)

class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6)
    is_admin: bool = False

class UsuarioLogin(BaseModel):
    nome_completo: str
    senha: str

class UsuarioResponse(UsuarioBase):
    id: int
    is_admin: bool
    ativo: bool
    data_cadastro: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioResponse

# Modelos de Sabor de Pizza
class SaborPizzaBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    preco_pedaco: float = Field(..., gt=0)

class SaborPizzaCreate(SaborPizzaBase):
    pass

class SaborPizzaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    preco_pedaco: Optional[float] = Field(None, gt=0)
    ativo: Optional[bool] = None

class SaborPizzaResponse(SaborPizzaBase):
    id: int
    ativo: bool
    data_cadastro: Optional[datetime] = None

# Modelos de Evento
# Modelos de Evento
class EventoBase(BaseModel):
    data_evento: date
    data_limite: datetime
    nome: Optional[str] = None 

class EventoCreate(EventoBase):
    pass

class EventoUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(ABERTO|FECHADO|FINALIZADO)$")
    data_limite: Optional[datetime] = None

class EventoResponse(EventoBase):
    id: int
    status: str
    data_criacao: Optional[datetime] = None

# Modelos de Pedido
class ItemPedidoCreate(BaseModel):
    sabor_id: int
    quantidade: int = Field(..., gt=0, le=8)

class ItemPedidoResponse(BaseModel):
    id: int
    sabor_id: int
    sabor_nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float

class PedidoCreate(BaseModel):
    evento_id: int
    itens: List[ItemPedidoCreate] = Field(..., min_items=1)

class PedidoResponse(BaseModel):
    id: int
    evento_id: int
    usuario_id: int
    usuario_nome: str
    usuario_setor: str
    valor_total: float
    valor_frete: float
    status: str
    data_pedido: Optional[datetime] = None
    itens: List[ItemPedidoResponse]

class PedidoUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(PENDENTE|CONFIRMADO|PAGO)$")

# Modelos de Dashboard
class EstatisticasPizza(BaseModel):
    sabor_id: int
    sabor_nome: str
    total_pedacos: int
    pizzas_completas: int  # quantas pizzas de 8 pedaços
    pedacos_restantes: int  # pedaços que não fecham uma pizza
    valor_total: float

class DashboardResponse(BaseModel):
    evento_id: int
    data_evento: date
    status: str
    total_participantes: int
    total_pedidos: int
    valor_total_evento: float
    estatisticas_por_sabor: List[EstatisticasPizza]

class ResumoEvento(BaseModel):
    evento: EventoResponse
    total_participantes: int
    total_pedidos: int
    total_pizzas: int
    valor_total: float
