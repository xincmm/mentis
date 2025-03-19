'use server';

import { Checkpoint } from './types';

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL;

export async function getHistory<TAgentState, TInterruptValue>(threadId: string): Promise<Checkpoint<TAgentState, TInterruptValue>[]> {
  const response = await fetch(`${AGENT_URL}/history?thread_id=${threadId}`);

  if (!response.ok) {
    try {
      // 尝试解析JSON错误
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch agent history');
    } catch (jsonError) {
      // 如果响应不是JSON格式，返回状态文本或通用错误
      throw new Error(`Failed to fetch agent history: ${response.statusText || response.status}`);
    }
  }

  try {
    const data = await response.json();
    return data as Checkpoint<TAgentState, TInterruptValue>[];
  } catch (error) {
    console.error('Error parsing history response:', error);
    throw new Error('Failed to parse agent history response');
  }
}

export async function stopAgent(threadId: string): Promise<void> {
  const response = await fetch(`${AGENT_URL}/agent/stop`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ thread_id: threadId }),
  });

  if (!response.ok) {
    try {
      // 尝试解析JSON错误
      const error = await response.json();
      throw new Error(error.detail || 'Failed to stop agent');
    } catch (jsonError) {
      // 如果响应不是JSON格式，返回状态文本或通用错误
      throw new Error(`Failed to stop agent: ${response.statusText || response.status}`);
    }
  }
}