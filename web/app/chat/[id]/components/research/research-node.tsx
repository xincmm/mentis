import { AgentState } from "../../agent-types";
import ResearchStatus from "./research-status";
import SearchResults from "./search-results";
import ReportPreview from "./report-preview";

interface ResearchNodeProps {
  nodeState: Partial<AgentState>;
}

export default function ResearchNode({ nodeState }: ResearchNodeProps) {
  // 根据节点名称渲染不同的组件
  if (nodeState?.node_type === "research_status") {
    return <ResearchStatus nodeState={nodeState} />;
  }
  
  if (nodeState?.node_type === "search_results") {
    return <SearchResults nodeState={nodeState} />;
  }
  
  if (nodeState?.node_type === "report_preview") {
    return <ReportPreview nodeState={nodeState} />;
  }
  
  return null;
}