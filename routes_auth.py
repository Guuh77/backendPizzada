from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from models import UsuarioCreate, UsuarioLogin, Token, UsuarioResponse
from auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token,
    get_current_user,
    get_current_admin_user
)
from database import execute_query, get_db_connection
from config import get_settings

router = APIRouter(prefix="/auth", tags=["Autenticação"])
settings = get_settings()

@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UsuarioCreate):
    """Registra um novo usuário"""
    
    # Verificar se usuário já existe
    check_query = "SELECT id FROM usuarios WHERE nome_completo = :nome"
    existing = execute_query(check_query, {"nome": user.nome_completo}, fetch_one=True)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já existe com este nome"
        )
    
    # Hash da senha
    hashed_password = get_password_hash(user.senha)
    
    # Inserir usuário
    insert_query = """
        INSERT INTO usuarios (nome_completo, senha_hash, setor, is_admin)
        VALUES (:nome, :senha, :setor, :admin)
    """
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            insert_query,
            {
                "nome": user.nome_completo,
                "senha": hashed_password,
                "setor": user.setor,
                "admin": 1 if user.is_admin else 0
            }
        )
        conn.commit()
        
        # Buscar o usuário criado
        select_query = """
            SELECT id, nome_completo, setor, is_admin, ativo, data_cadastro
            FROM usuarios
            WHERE nome_completo = :nome
        """
        cursor.execute(select_query, {"nome": user.nome_completo})
        result = cursor.fetchone()
        cursor.close()
    
    return UsuarioResponse(
        id=result[0],
        nome_completo=result[1],
        setor=result[2],
        is_admin=bool(result[3]),
        ativo=bool(result[4]),
        data_cadastro=result[5]
    )

@router.post("/login", response_model=Token)
async def login(credentials: UsuarioLogin):
    """Faz login do usuário"""
    
    user = authenticate_user(credentials.nome_completo, credentials.senha)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["id"])}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UsuarioResponse(
            id=user["id"],
            nome_completo=user["nome_completo"],
            setor=user["setor"],
            is_admin=user["is_admin"],
            ativo=user["ativo"],
            data_cadastro=user["data_cadastro"]
        )
    )

@router.get("/me", response_model=UsuarioResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna dados do usuário logado"""
    return UsuarioResponse(
        id=current_user["id"],
        nome_completo=current_user["nome_completo"],
        setor=current_user["setor"],
        is_admin=current_user["is_admin"],
        ativo=current_user["ativo"],
        data_cadastro=current_user["data_cadastro"]
    )
