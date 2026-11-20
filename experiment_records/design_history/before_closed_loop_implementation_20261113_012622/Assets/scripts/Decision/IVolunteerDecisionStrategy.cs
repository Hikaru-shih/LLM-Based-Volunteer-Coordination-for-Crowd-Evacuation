namespace Decision
{
    public interface IVolunteerDecisionStrategy
    {
        bool ShouldVolunteer(VolunteerDecisionContext context);
    }
}
