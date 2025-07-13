"""
Example script showing how to use the evaluation export functionality
"""

import asyncio
from evaluator import Evaluator

async def main():
    # Initialize evaluator
    evaluator = Evaluator()
    
    # Get available pipelines and LLM providers
    pipelines = evaluator.get_available_pipelines()
    llm_providers = evaluator.get_available_llm_providers()
    
    print(f"Available pipelines: {pipelines}")
    print(f"Available LLM providers: {llm_providers}")
    
    # Run a sample evaluation (5 questions, max difficulty 2)
    print("\nRunning sample evaluation...")
    results = await evaluator.evaluate_sample_questions(
        pipeline_names=pipelines[:2],  # Use first 2 pipelines
        llm_providers=llm_providers[:1],  # Use first LLM provider
        question_count=5,
        max_difficulty=2
    )
    
    print(f"Completed {len(results)} evaluations")
    
    # Export results in different formats
    print("\nExporting results...")
    
    # Option 1: Export to specific files
    evaluator.export_results_to_json(results, "evaluation_results.json")
    evaluator.export_results_to_csv(results, "evaluation_results.csv")
    
    # Option 2: Export with timestamp (recommended)
    exported_files = evaluator.export_results_with_timestamp(
        results, 
        "sample_evaluation", 
        formats=["json", "csv"],
        output_dir="evaluation_exports"
    )
    
    print(f"Exported files: {exported_files}")
    
    # Print summary
    summary = evaluator.get_evaluation_summary(results)
    print(f"\nEvaluation Summary:")
    print(f"Total evaluations: {summary['total_evaluations']}")
    print(f"Success rate: {summary['success_rate']:.2%}")
    print(f"Total cost: ${summary['total_cost']:.4f}")
    print(f"Average execution time: {summary['avg_execution_time']:.2f}s")

if __name__ == "__main__":
    asyncio.run(main()) 