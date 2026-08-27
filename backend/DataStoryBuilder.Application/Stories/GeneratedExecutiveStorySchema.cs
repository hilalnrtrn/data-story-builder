namespace DataStoryBuilder.Application.Stories;

public static class GeneratedExecutiveStorySchema
{
    public static string Build() =>
        """
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["title", "executiveSummary", "sections"],
          "properties": {
            "title": { "type": "string", "minLength": 1 },
            "executiveSummary": { "type": "string", "minLength": 1 },
            "sections": {
              "type": "array",
              "minItems": 1,
              "items": {
                "type": "object",
                "additionalProperties": false,
                "required": ["order", "type", "items"],
                "properties": {
                  "order": { "type": "integer", "minimum": 1 },
                  "type": { "type": "string", "minLength": 1 },
                  "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                      "type": "object",
                      "additionalProperties": false,
                      "required": ["sourceItemId", "text"],
                      "properties": {
                        "sourceItemId": { "type": "string", "minLength": 1 },
                        "text": { "type": "string", "minLength": 1 }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """;
}
