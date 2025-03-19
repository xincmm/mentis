import { AgentState } from "../../agent-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";

interface ReportPreviewProps {
  nodeState: Partial<AgentState>;
}

export default function ReportPreview({ nodeState }: ReportPreviewProps) {
  if (!nodeState?.report_content) {
    return null;
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="p-3 pb-0">
        <CardTitle className="text-sm flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Research Report
        </CardTitle>
      </CardHeader>
      <CardContent className="p-3 pt-1">
        <div className="prose prose-sm max-w-none">
          <div dangerouslySetInnerHTML={{ __html: nodeState.report_content }} />
        </div>
      </CardContent>
    </Card>
  );
}