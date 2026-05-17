from pydantic import BaseModel, Field

from client.bini import BiniClient


class CallCenterHtmlValidation(BaseModel):

    model_config = {'extra': 'forbid'}

    section_titles_match_output_language: bool = Field(...,
                                                       description="True if all section titles are translated to the main output language")
    highlights_bullet_word_limit: bool = Field(...,
                                               description="True if each Call Highlights bullet has a maximum of 15 words")
    sentiment_format_strict: bool = Field(...,
                                          description="True if Sentiment strictly follows the required 3-line format")
    pii_and_sensitive_data_masked: bool = Field(...,
                                                description="True if sensitive data (PHI, account numbers, IDs) is removed or masked")
    vertical_specific_rules_applied: bool = Field(...,
                                                  description="True if industry-specific handling is applied correctly when vertical detected")
    no_raw_quotes_or_timestamps: bool = Field(...,
                                              description="True if no verbatim quotes, timestamps, or speaker turns are included")
    no_hallucinated_tickets_or_dates: bool = Field(...,
                                                   description="True if tickets and dates are included only if mentioned, otherwise marked N/A or TBD")

    # Agent Quality Fields - TRUE means GOOD/COMPLIANT behavior, FALSE means problems detected
    agent_statements_accurate: bool = Field(...,
                                            description="True if the agent provided accurate, truthful information with no misstatements or misleading claims. False if the summary shows agent gave incorrect or misleading information.")
    promises_properly_supported: bool = Field(...,
                                              description="True if all agent promises (refunds, timelines, outcomes) are backed by clear authority or policy. False if agent made unsupported or unauthorized promises.")
    timelines_realistic: bool = Field(...,
                                      description="True if any timelines mentioned by agent are reasonable and properly qualified. False if agent stated unrealistic or guaranteed timelines.")
    policy_compliance_maintained: bool = Field(...,
                                               description="True if the call shows no policy, regulatory, or compliance concerns. False if potential compliance risks are evident.")
    customer_expectations_aligned: bool = Field(...,
                                                description="True if agent statements align with actual processes and policies. False if there's a mismatch that could mislead the customer.")
    agent_conduct_professional: bool = Field(...,
                                             description="True if the agent was professional, respectful, and appropriate throughout. False if the summary shows unprofessional, dismissive, or inappropriate behavior.")
    no_escalation_needed: bool = Field(...,
                                       description="True if the call was handled properly with no need for escalation or remediation. False if coaching, escalation, or remediation is recommended.")


bini = BiniClient(host='10.8.2.35', port=8082)
for each in range(10):
    print(bini.run_text('hi', schema_output=CallCenterHtmlValidation))
