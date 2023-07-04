def migrate(cr, version):
    # customization has parent, child
    # oob has child, parent.
    query = """
    INSERT INTO task_dependencies_rel(task_id, depends_on_id)
    SELECT depending_task_id, task_id from project_depending_tasks
    """
    cr.execute(query)
