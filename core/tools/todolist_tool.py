from typing import Dict, List, Optional
from langchain_core.tools import BaseTool
import re
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('todolist_tool')

class TodolistTool(BaseTool):
    """Tool for managing a todolist.
    
    This tool provides functionality to create, view, and update a todolist.
    """
    name: str = "todolist"
    description: str = "Manage a todolist with create, view, add task, and update operations"
    
    def __init__(self):
        """Initialize the todolist tool."""
        super().__init__()
        self._todolist = ""
    
    def _run(self, action: str, **kwargs) -> str:
        """Run the todolist tool with the specified action.
        
        Args:
            action: The action to perform (create, view, update, etc.)
            **kwargs: Additional arguments for the specific action
            
        Returns:
            The result of the action
        """
        logger.info(f"TodolistTool._run called with action: {action}, kwargs: {kwargs}")
        
        # Handle variations of 'add task' action
        if action.startswith("add task") or action == "add_task" or action == "add":
            # 级联检查多种可能的参数名称
            task_description = kwargs.get("task_description", "")
            if not task_description:
                task_description = kwargs.get("task", "")
            if not task_description:
                task_description = kwargs.get("content", "")
                
            # If no task_description provided through parameters, try to extract it from the action string
            if not task_description and len(action) > 8:  # 'add task' is 8 chars
                # Extract task description from action like "add task: Get a joke about tech companies"
                parts = action.split(":", 1)
                if len(parts) > 1:
                    task_description = parts[1].strip()
                else:
                    # Try extracting after "add task" without colon
                    parts = action.split("add task", 1)
                    if len(parts) > 1:
                        task_description = parts[1].strip()
            
            if not task_description or task_description.strip() == "":
                error_msg = "No task description provided. Please provide a task description."
                logger.error(error_msg)
                return error_msg
                
            result = self.add_task(task_description)
            logger.info(f"TodolistTool.add_task result: {result[:100]}..." if len(result) > 100 else f"TodolistTool.add_task result: {result}")
            return result
        elif action == "create":
            plan_content = kwargs.get("plan_content", "")
            if not plan_content or plan_content.strip() == "":
                error_msg = "No plan content provided. Please provide a plan with tasks."
                logger.error(error_msg)
                return error_msg
                
            result = self.create_todolist(plan_content)
            logger.info(f"TodolistTool.create_todolist result: {result[:100]}..." if len(result) > 100 else f"TodolistTool.create_todolist result: {result}")
            return result
        elif action == "view":
            result = self.get_todolist()
            logger.info(f"TodolistTool.get_todolist result: {result[:100]}..." if len(result) > 100 else f"TodolistTool.get_todolist result: {result}")
            return result
        elif action == "update_by_index":
            task_index = kwargs.get("task_index")
            if task_index is None:
                error_msg = "No task index provided. Please provide a task index."
                logger.error(error_msg)
                return error_msg
                
            try:
                task_index = int(task_index)
            except (ValueError, TypeError):
                error_msg = f"Invalid task index: {task_index}. Please provide a valid integer."
                logger.error(error_msg)
                return error_msg
                
            result = self.update_task_status(
                task_index,
                kwargs.get("completed", True)
            )
            logger.info(f"TodolistTool.update_task_status result: {result[:100]}..." if len(result) > 100 else f"TodolistTool.update_task_status result: {result}")
            return result
        elif action == "update_by_description":
            task_description = kwargs.get("task_description", "")
            if not task_description or task_description.strip() == "":
                error_msg = "No task description provided. Please provide a task description."
                logger.error(error_msg)
                return error_msg
                
            result = self.update_task_by_description(
                task_description,
                kwargs.get("completed", True)
            )
            logger.info(f"TodolistTool.update_task_by_description result: {result[:100]}..." if len(result) > 100 else f"TodolistTool.update_task_by_description result: {result}")
            return result
        else:
            error_msg = f"Unknown action: {action}. Available actions: create, view, add task, update_by_index, update_by_description"
            logger.error(error_msg)
            return error_msg
    
    async def _arun(self, action: str, **kwargs) -> str:
        """Run the todolist tool asynchronously."""
        return self._run(action, **kwargs)
    
    def create_todolist(self, plan_content: str) -> str:
        """Convert the plan content into a Markdown todolist.

        Args:
            plan_content: The original plan content. Should be formatted as a Markdown todolist
                          or a list of tasks that can be easily converted to a todolist.

        Returns:
            The Markdown todolist.
        """
        logger.info(f"TodolistTool.create_todolist called with plan_content: {plan_content[:100]}..." if len(plan_content) > 100 else f"TodolistTool.create_todolist called with plan_content: {plan_content}")
        
        if not plan_content or plan_content.strip() == "":
            logger.warning("Empty plan content provided to create_todolist")
            return "No tasks were provided. Please provide a plan with tasks."
        
        # 解析策略
        tasks = []
        
        # 首先检查是否已经是Markdown格式的todolist
        markdown_todo_pattern = r'- \[ \] (.+)'
        markdown_todos = re.findall(markdown_todo_pattern, plan_content)
        
        if markdown_todos:
            # 如果已经是Markdown格式的todolist，直接使用
            logger.info(f"Found {len(markdown_todos)} tasks in Markdown todolist format")
            tasks.extend(markdown_todos)
        else:
            # 尝试匹配列表格式 (带有数字、星号或减号的项目)
            try:
                # 简化的正则表达式，避免复杂的嵌套结构
                list_pattern = r'(?:^|\n)[ \t]*(?:[\*\-]|\d+\.)[ \t]+([^\n]+)'
                list_items = re.findall(list_pattern, plan_content)
                if list_items:
                    logger.info(f"Found {len(list_items)} list items")
                    tasks.extend([item.strip() for item in list_items if item.strip()])
                else:
                    # 如果没有找到列表格式，按行分割
                    lines = [line.strip() for line in plan_content.split('\n') if line.strip()]
                    # 过滤掉标题和短行
                    potential_tasks = [line for line in lines 
                                    if not line.startswith('#') 
                                    and len(line) > 10]
                    tasks.extend(potential_tasks)
            except Exception as e:
                logger.error(f"Error parsing plan content: {str(e)}")
                # 如果正则表达式失败，简单地按行分割
                lines = [line.strip() for line in plan_content.split('\n') if line.strip()]
                tasks.extend([line for line in lines if len(line) > 10])
        
        # 确保任务不重复
        unique_tasks = []
        for task in tasks:
            # 移除任何已有的checkbox标记
            task = re.sub(r'^\[[ x]\]\s*', '', task)
            normalized = re.sub(r'\s+', ' ', task.lower())
            if not any(re.sub(r'\s+', ' ', t.lower()) == normalized for t in unique_tasks):
                unique_tasks.append(task)
        
        # 创建todolist格式
        if unique_tasks:
            todolist = [f"- [ ] {task}" for task in unique_tasks]
            self._todolist = "\n".join(todolist)
            logger.info(f"Created todolist with {len(todolist)} tasks")
            return self._todolist
        else:
            logger.warning("No tasks could be extracted from the plan content")
            return "Could not extract any tasks from the provided plan. Please provide a clearer task list."
    
    def update_task_status(self, task_index: int, completed: bool = True) -> str:
        """Update the completion status of a specific task.

        Args:
            task_index: The index of the task (starting from 0).
            completed: Whether the task is completed.

        Returns:
            The updated todolist.
        """
        logger.info(f"TodolistTool.update_task_status called with task_index: {task_index}, completed: {completed}")
        
        if not self._todolist:
            logger.warning("No todolist exists when trying to update task status")
            return "There is no todolist currently, please create one first."

        tasks = self._todolist.split('\n')
        logger.info(f"Current todolist has {len(tasks)} tasks")
        
        if task_index < 0 or task_index >= len(tasks):
            error_msg = f"Task index {task_index} is out of range, there are currently {len(tasks)} tasks."
            logger.error(error_msg)
            return error_msg

        # Update task status
        task = tasks[task_index]
        logger.info(f"Updating task: '{task}' to completed={completed}")
        tasks[task_index] = task.replace('[ ]', '[x]') if completed else task.replace('[x]', '[ ]')
        self._todolist = "\n".join(tasks)
        return self._todolist
    
    def update_task_by_description(self, task_description: str, completed: bool = True) -> str:
        """Update task status based on task description.

        Args:
            task_description: The task description (partial match is sufficient).
            completed: Whether the task is completed.

        Returns:
            The updated todolist.
        """
        logger.info(f"TodolistTool.update_task_by_description called with task_description: '{task_description}', completed: {completed}")
        
        if not self._todolist:
            logger.warning("No todolist exists when trying to update task by description")
            return "There is no todolist currently, please create one first."

        tasks = self._todolist.split('\n')
        logger.info(f"Current todolist has {len(tasks)} tasks")
        
        found = False
        for i, task in enumerate(tasks):
            # Extract the task description part (remove status markers)
            task_content = re.sub(r'^- \[[ x]\]\s*', '', task)

            # If the task description contains the specified description, update the status
            if task_description.lower() in task_content.lower():
                logger.info(f"Found matching task at index {i}: '{task}'")
                tasks[i] = task.replace('[ ]', '[x]') if completed else task.replace('[x]', '[ ]')
                found = True

        if not found:
            error_msg = f"No task containing '{task_description}' was found."
            logger.warning(error_msg)
            return error_msg

        self._todolist = "\n".join(tasks)
        logger.info(f"Updated todolist with {len(tasks)} tasks")
        return self._todolist
    
    def get_todolist(self) -> str:
        """Get the current todolist.

        Returns:
            The current todolist.
        """
        logger.info("TodolistTool.get_todolist called")
        if not self._todolist:
            logger.warning("No todolist exists when trying to get todolist")
            return "There is no todolist currently, please create one first."
        else:
            #logger.info(f"Returning todolist with {len(self._todolist.split('\n'))} tasks")
            return self._todolist
            
    def add_task(self, task_description: str) -> str:
        """Add a new task to the todolist.

        Args:
            task_description: The description of the task to add.

        Returns:
            The updated todolist.
        """
        logger.info(f"TodolistTool.add_task called with task_description: '{task_description}'")
        
        if not task_description or task_description.strip() == "":
            warning_msg = "Cannot add an empty task. Please provide a task description."
            logger.warning(warning_msg)
            return warning_msg
        
        # Clean up the task description
        task_description = task_description.strip()
        
        # Remove any existing markdown list markers or checkbox notation
        task_description = re.sub(r'^[\*\-\d\.\)]+\s*', '', task_description)
        task_description = re.sub(r'^\[[ x]\]\s*', '', task_description)
        
        # If todolist doesn't exist yet, create an empty one
        if not self._todolist:
            self._todolist = ""
        
        # Add the new task
        new_task = f"- [ ] {task_description}"
        
        if self._todolist:
            self._todolist = f"{self._todolist}\n{new_task}"
        else:
            self._todolist = new_task
            
        logger.info(f"Added new task: '{new_task}'")
        return self._todolist