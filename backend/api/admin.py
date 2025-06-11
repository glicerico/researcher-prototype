from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime

from services.auth_manager import auth_manager, verify_admin_token
from services.prompt_manager import prompt_manager
from services.flow_analyzer import flow_analyzer
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request/response
class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PromptUpdateRequest(BaseModel):
    content: str


class PromptTestRequest(BaseModel):
    variables: Dict[str, str]


class RestorePromptRequest(BaseModel):
    backup_filename: str


# Authentication endpoints
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Admin login endpoint."""
    try:
        if not auth_manager.verify_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = auth_manager.create_access_token()
        
        logger.info("Admin login successful")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=auth_manager.expire_minutes * 60  # Convert to seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify admin token validity."""
    try:
        verify_admin_token(authorization)
        return {"valid": True, "message": "Token is valid"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token verification"
        )


# Prompt management endpoints
@router.get("/prompts")
async def get_all_prompts(authorization: Optional[str] = Header(None)):
    """Get all prompts with metadata."""
    verify_admin_token(authorization)
    
    try:
        prompts = prompt_manager.get_all_prompts()
        
        # Group prompts by category for better organization
        grouped_prompts = {}
        for prompt_name, prompt_data in prompts.items():
            category = prompt_data['category']
            if category not in grouped_prompts:
                grouped_prompts[category] = []
            
            grouped_prompts[category].append({
                'name': prompt_name,
                'description': prompt_data['description'],
                'variables': prompt_data['variables'],
                'content_length': len(prompt_data['content'])
            })
        
        return {
            'total_prompts': len(prompts),
            'categories': grouped_prompts,
            'prompts': prompts
        }
        
    except Exception as e:
        logger.error(f"Error getting prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompts: {str(e)}"
        )


@router.get("/prompts/{prompt_name}")
async def get_prompt(prompt_name: str, authorization: Optional[str] = Header(None)):
    """Get a specific prompt by name."""
    verify_admin_token(authorization)
    
    try:
        prompt = prompt_manager.get_prompt(prompt_name)
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{prompt_name}' not found"
            )
        
        return prompt
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt: {str(e)}"
        )


@router.put("/prompts/{prompt_name}")
async def update_prompt(
    prompt_name: str, 
    request: PromptUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """Update a specific prompt."""
    verify_admin_token(authorization)
    
    try:
        # Get admin user from token (for audit trail)
        token = authorization.replace("Bearer ", "")
        payload = auth_manager.get_token_payload(token)
        admin_user = payload.get("sub", "admin") if payload else "admin"
        
        success = prompt_manager.update_prompt(prompt_name, request.content, admin_user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update prompt '{prompt_name}'"
            )
        
        # Get updated prompt to return
        updated_prompt = prompt_manager.get_prompt(prompt_name)
        
        logger.info(f"Admin {admin_user} updated prompt {prompt_name}")
        
        return {
            'success': True,
            'message': f"Prompt '{prompt_name}' updated successfully",
            'prompt': updated_prompt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating prompt: {str(e)}"
        )


@router.get("/prompts/{prompt_name}/history")
async def get_prompt_history(prompt_name: str, authorization: Optional[str] = Header(None)):
    """Get version history for a specific prompt."""
    verify_admin_token(authorization)
    
    try:
        history = prompt_manager.get_prompt_history(prompt_name)
        
        return {
            'prompt_name': prompt_name,
            'total_versions': len(history),
            'history': history
        }
        
    except Exception as e:
        logger.error(f"Error getting history for prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt history: {str(e)}"
        )


@router.post("/prompts/{prompt_name}/restore")
async def restore_prompt(
    prompt_name: str,
    request: RestorePromptRequest,
    authorization: Optional[str] = Header(None)
):
    """Restore a prompt from a backup."""
    verify_admin_token(authorization)
    
    try:
        # Get admin user from token (for audit trail)
        token = authorization.replace("Bearer ", "")
        payload = auth_manager.get_token_payload(token)
        admin_user = payload.get("sub", "admin") if payload else "admin"
        
        success = prompt_manager.restore_prompt(prompt_name, request.backup_filename, admin_user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to restore prompt '{prompt_name}' from backup '{request.backup_filename}'"
            )
        
        # Get restored prompt to return
        restored_prompt = prompt_manager.get_prompt(prompt_name)
        
        logger.info(f"Admin {admin_user} restored prompt {prompt_name} from {request.backup_filename}")
        
        return {
            'success': True,
            'message': f"Prompt '{prompt_name}' restored successfully from '{request.backup_filename}'",
            'prompt': restored_prompt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring prompt: {str(e)}"
        )


@router.post("/prompts/{prompt_name}/test")
async def test_prompt(
    prompt_name: str,
    request: PromptTestRequest,
    authorization: Optional[str] = Header(None)
):
    """Test a prompt with provided variables."""
    verify_admin_token(authorization)
    
    try:
        result = prompt_manager.test_prompt(prompt_name, request.variables)
        
        return {
            'prompt_name': prompt_name,
            'test_result': result
        }
        
    except Exception as e:
        logger.error(f"Error testing prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing prompt: {str(e)}"
        )


# Status endpoint
@router.get("/status")
async def get_admin_status(authorization: Optional[str] = Header(None)):
    """Get admin interface status."""
    verify_admin_token(authorization)
    
    try:
        # Get some basic stats
        prompts = prompt_manager.get_all_prompts()
        
        # Count backups
        backup_count = 0
        try:
            backup_dir = prompt_manager.backup_dir
            if backup_dir.exists():
                backup_count = len(list(backup_dir.glob("*.json")))
        except:
            pass
        
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'prompts_loaded': len(prompts),
            'backup_files': backup_count,
            'categories': list(set([p['category'] for p in prompts.values()]))
        }
        
    except Exception as e:
        logger.error(f"Error getting admin status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting admin status: {str(e)}"
        )


# Flow visualization endpoints
@router.get("/flows")
async def get_flow_summary(authorization: Optional[str] = Header(None)):
    """Get summary of all LangGraph flows and their prompt usage."""
    verify_admin_token(authorization)
    
    try:
        summary = flow_analyzer.get_flow_summary()
        
        return {
            'success': True,
            'flow_summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting flow summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving flow summary: {str(e)}"
        )


@router.get("/flows/prompt-usage")
async def get_prompt_usage_map(authorization: Optional[str] = Header(None)):
    """Get mapping of prompts to the nodes that use them."""
    verify_admin_token(authorization)
    
    try:
        prompt_usage = flow_analyzer.get_prompt_usage_map()
        
        return {
            'success': True,
            'prompt_usage': prompt_usage,
            'total_prompts': len(prompt_usage),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting prompt usage map: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt usage map: {str(e)}"
        )


@router.get("/flows/nodes/{node_id}")
async def get_node_info(node_id: str, authorization: Optional[str] = Header(None)):
    """Get detailed information about a specific node including its prompt."""
    verify_admin_token(authorization)
    
    try:
        node_info = flow_analyzer.get_node_prompt_info(node_id)
        
        if not node_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{node_id}' not found"
            )
        
        # If the node has a prompt, get the full prompt details
        prompt_details = None
        if node_info.get('prompt'):
            prompt_name = node_info['prompt']
            prompt_details = prompt_manager.get_prompt(prompt_name)
        
        return {
            'success': True,
            'node_id': node_id,
            'node_info': node_info,
            'prompt_details': prompt_details,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node info for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving node information: {str(e)}"
        )


@router.post("/flows/diagrams/generate")
async def generate_flow_diagrams(authorization: Optional[str] = Header(None)):
    """Generate flow diagrams for both main chat and research graphs."""
    verify_admin_token(authorization)
    
    try:
        # Get admin user from token (for audit trail)
        token = authorization.replace("Bearer ", "")
        payload = auth_manager.get_token_payload(token)
        admin_user = payload.get("sub", "admin") if payload else "admin"
        
        # Generate diagrams
        result = flow_analyzer.generate_flow_diagrams()
        
        # Save metadata for frontend consumption
        metadata_saved = flow_analyzer.save_flow_metadata()
        
        logger.info(f"Admin {admin_user} generated flow diagrams")
        
        return {
            'success': result['success'],
            'diagrams': result['diagrams'],
            'errors': result['errors'],
            'metadata_saved': metadata_saved,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating flow diagrams: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating flow diagrams: {str(e)}"
        )


@router.get("/flows/{graph_type}")
async def get_flow_data(graph_type: str, authorization: Optional[str] = Header(None)):
    """Get detailed flow data for a specific graph type (main or research)."""
    verify_admin_token(authorization)
    
    if graph_type not in ["main", "research"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Graph type must be 'main' or 'research'"
        )
    
    try:
        flow_data = flow_analyzer.get_flow_data(graph_type)
        
        return {
            'success': True,
            'graph_type': graph_type,
            'flow_data': flow_data,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting flow data for {graph_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving flow data: {str(e)}"
        ) 