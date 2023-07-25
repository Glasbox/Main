def migrate(cr, version):
    # customization has parent, child
    # oob has child, parent.
    query = """
    delete from project_depending_tasks where task_id=depending_task_id;
    delete from project_depending_tasks where id not in (select max(id) 
										   from project_depending_tasks
										  group by task_id, depending_task_id);
    INSERT INTO task_dependencies_rel(task_id, depends_on_id)
    SELECT depending_task_id, task_id FROM project_depending_tasks;
    """
    cr.execute(query)
    