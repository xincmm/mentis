import { AgentState } from "../../agent-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";

interface SearchResultsProps {
  nodeState: Partial<AgentState>;
}

export default function SearchResults({ nodeState }: SearchResultsProps) {
  if (!nodeState?.search_results?.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      {nodeState.search_results.map((result, index) => (
        <Card key={index} className="overflow-hidden">
          <CardHeader className="p-3 pb-0">
            <CardTitle className="text-sm flex items-center gap-2">
              <a 
                href={result.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline flex items-center gap-1"
              >
                {result.title}
                <ExternalLink className="h-3 w-3" />
              </a>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-1">
            <p className="text-xs text-muted-foreground">{result.snippet}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}