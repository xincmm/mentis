import { AgentState } from "../../agent-types";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface ResearchStatusProps {
  nodeState: Partial<AgentState>;
}

export default function ResearchStatus({ nodeState }: ResearchStatusProps) {
  if (!nodeState?.research_status?.[0]) {
    return null;
  }

  const { topic, status, progress } = nodeState.research_status[0];

  return (
    <div className="flex justify-end">
      <Card className="inline-block">
        <CardContent className="p-2">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <div className="text-sm font-medium">{topic}</div>
            </div>
            <div className="text-xs text-muted-foreground">{status}</div>
            {progress !== undefined && (
              <Progress value={progress} className="h-1" />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}